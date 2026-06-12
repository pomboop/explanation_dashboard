from flask import Flask, jsonify, render_template
from pathlib import Path   # used to locate interaction_log.txt next to app.py
import re                  # used to parse log lines with regex
import shlex               # used to safely parse BT key="value" log fields


app = Flask(__name__)


# Path to the interaction log file written by llm_agent.py, bt_server.py, and tello_controller.py
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "interaction_log.txt"


# Regex pattern to parse every log line into timestamp, level, and payload
# Supports both colon-style (USER_PROMPT: takeoff) and key-value style (BT_STATUS source_component="bt" ...)
LOG_PREFIX_RE = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - '
    r'(?P<level>[A-Z]+) - '
    r'(?P<payload>.*)$'
)


# Keyword groups used to classify USER_PROMPT commands into dashboard states
MOVEMENT_KEYWORDS = [
    "takeoff", "take off", "land", "move", "turn", "rotate", "forward",
    "backward", "backwards", "left", "right", "up", "down", "flip"
]
TRACKING_KEYWORDS = ["track", "follow", "tracking"]
STATUS_KEYWORDS = ["status", "state"]
BATTERY_KEYWORDS = ["battery"]


# Returns safe fallback values shown on the dashboard when the log is empty or missing
def default_state():
    return {
        "mode": "log",
        "system_state": "idle",
        "source": "Log file",
        "timestamp": "—",
        "understood": "Waiting for command...",
        "status": "Idle",
        "outcome": "No issues reported.",
        "battery": "Unknown",
        "battery_label": "Unknown",
        "raw_event": None,
        "raw_message": "",
        "recent_entries": [],
    }


# Removes terminal escape characters that sometimes appear in log messages
def clean_message(message: str) -> str:
    text = (message or "").strip()
    text = text.replace("\x1b[A", "").replace("\x1b[D", "").strip()
    return " ".join(text.split())


# Parses BT-style key="value" fields into a dictionary
# Example: source_component="bt" bt_name="simple_bt" bt_status="RUNNING"
def parse_kv_message(text: str):
    try:
        parts = shlex.split(text)
    except ValueError:
        return {}

    data = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        data[key] = value
    return data


# Parses a raw log line into structured fields (timestamp, level, event, message, fields)
# Handles both colon-style events (USER_PROMPT: takeoff) and BT key-value events (BT_STATUS ...)
def parse_line(line: str):
    match = LOG_PREFIX_RE.match(line.strip())
    if not match:
        return None

    data = match.groupdict()
    payload = data["payload"].strip()

    parsed = {
        "timestamp": data["timestamp"],
        "level": data["level"],
        "event": None,
        "message": "",
        "fields": {},
        "raw": payload,
    }

    # Old style: EVENT: message (e.g. USER_PROMPT: takeoff, TOOL_START: takeoff source_component=agent)
    if ": " in payload:
        event, message = payload.split(": ", 1)
        parsed["event"] = event.strip()
        # Strip trailing source_component tag so it does not appear in dashboard display text
        message = re.sub(r'\s*source_component=\S+', '', message)
        parsed["message"] = clean_message(message)
        return parsed

    # BT key-value style: EVENT key="value" key2="value2"
    parts = payload.split(" ", 1)
    parsed["event"] = parts[0].strip()

    if len(parts) > 1:
        parsed["fields"] = parse_kv_message(parts[1])
        parsed["message"] = clean_message(parts[1])

    return parsed


# Classifies a USER_PROMPT into a system state and source using keyword matching
# Used to fill dashboard fields when no structured execution events are available yet
def classify_prompt(prompt: str):
    lowered = prompt.lower()

    if any(word in lowered for word in BATTERY_KEYWORDS):
        return {
            "system_state": "idle",
            "source": "Log file / battery query",
            "status": "Waiting for battery update from robot logs.",
            "outcome": "The current log shows a battery question, but no machine-readable battery value was found yet.",
        }

    if any(word in lowered for word in STATUS_KEYWORDS):
        return {
            "system_state": "idle",
            "source": "Log file / status query",
            "status": "Waiting for robot state update.",
            "outcome": "The current log shows a status question, but it does not contain a reliable final state entry for this request.",
        }

    if any(word in lowered for word in TRACKING_KEYWORDS):
        return {
            "system_state": "running",
            "source": "Log file / tracking command",
            "status": "Tracking-related command detected.",
            "outcome": "The log confirms the command was issued, but it does not yet confirm success or failure.",
        }

    if any(word in lowered for word in MOVEMENT_KEYWORDS):
        return {
            "system_state": "running",
            "source": "Log file / movement command",
            "status": "Movement-related command detected.",
            "outcome": "The log confirms the command was issued, but it does not yet contain an explicit completion event.",
        }

    return {
        "system_state": "idle",
        "source": "Log file / general query",
        "status": "General interaction detected.",
        "outcome": "No structured execution result was found for this entry.",
    }


# Converts a numeric battery percentage into a display label: Full, Medium, Low, or Unknown
# Full >= 70%, Medium >= 30%, Low < 30%
def battery_label_from_value(battery_value: str):
    if not battery_value or battery_value == "Unknown":
        return "Unknown"
    try:
        pct = int(str(battery_value).replace("%", ""))
    except ValueError:
        return "Unknown"

    if pct >= 70:
        return "Full"
    if pct >= 30:
        return "Medium"
    return "Low"


# Searches the log from the bottom up for the most recent battery value
# Supports BATTERY_UPDATE: robot=tello, percent=83.0 from tello_controller.py
def extract_battery(lines):
    for line in reversed(lines):
        parsed = parse_line(line)
        if not parsed:
            continue

        if parsed["event"] == "BATTERY_UPDATE":
            msg = parsed["message"]
            match = re.search(r'percent=(\d+(?:\.\d+)?)', msg)
            if match:
                return f"{int(float(match.group(1)))}%"

        fields = parsed.get("fields", {})
        if "battery_percent" in fields:
            try:
                return f"{int(float(fields['battery_percent']))}%"
            except ValueError:
                pass

    return "Unknown"


# Collects the most recent meaningful log entries for the dashboard activity panel
# Includes agent events (TOOL_START, FINAL_RESPONSE) and BT events (BT_STATUS, BT_ERROR)
def extract_recent_entries(lines, limit=12):
    recent = []

    for line in reversed(lines):
        parsed = parse_line(line)
        if not parsed:
            continue

        event = parsed["event"]

        if event not in {
            "USER_PROMPT",
            "TOOL_START",
            "TOOL_END",
            "FINAL_RESPONSE",
            "ERROR",
            "SEND_QUERY_ERROR",
            "BT_STATUS",
            "BT_ERROR",
            "BT_STOPPED_ON_FAILURE",
            "BT_BOOTSTRAP_FAILURE",
            "BATTERY_UPDATE",
            "BATTERY_WARNING",
        }:
            continue

        display_message = parsed["message"]

        # Format BT_STATUS fields into a readable single line for the activity panel
        if event == "BT_STATUS":
            fields = parsed.get("fields", {})
            display_message = (
                f'bt_status={fields.get("bt_status", "UNKNOWN")}, '
                f'system_state={fields.get("system_state", "unknown")}, '
                f'active_node={fields.get("active_node", "")}'
            )

        # For BT errors, show the failure reason directly instead of raw field text
        elif event in {"BT_ERROR", "BT_STOPPED_ON_FAILURE", "BT_BOOTSTRAP_FAILURE"}:
            fields = parsed.get("fields", {})
            display_message = fields.get("failure_reason", parsed["message"])

        if not display_message:
            continue

        recent.append({
            "timestamp": parsed["timestamp"],
            "event": event,
            "message": display_message,
        })

        if len(recent) >= limit:
            break

    return recent


# Main function that reads interaction_log.txt and returns structured dashboard data as a dict
def parse_current_log():
    state = default_state()

    # Return fallback state if the log file doesn't exist yet
    if not LOG_FILE.exists():
        state["outcome"] = "interaction_log.txt was not found next to app.py."
        return state

    raw_lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    lines = [line for line in raw_lines if line.strip()]

    # Extract battery and recent activity from the full log
    state["battery"] = extract_battery(lines)
    state["battery_label"] = battery_label_from_value(state["battery"])
    state["recent_entries"] = extract_recent_entries(lines)

    # If a battery warning was logged, force battery label to Low
    for line in reversed(lines):
        parsed = parse_line(line)
        if parsed and parsed["event"] == "BATTERY_WARNING":
            state["battery_label"] = "Low"
            break

    # Find the most recent instance of each relevant event type by scanning from the bottom
    latest_prompt = None
    latest_final_response = None
    latest_tool_start = None
    latest_bt_status = None
    latest_bt_error = None

    for line in reversed(lines):
        parsed = parse_line(line)
        if not parsed:
            continue

        event = parsed["event"]

        if latest_prompt is None and event == "USER_PROMPT" and parsed["message"]:
            latest_prompt = parsed

        if latest_final_response is None and event == "FINAL_RESPONSE" and parsed["message"]:
            latest_final_response = parsed

        if latest_tool_start is None and event == "TOOL_START" and parsed["message"]:
            latest_tool_start = parsed

        if latest_bt_status is None and event == "BT_STATUS":
            latest_bt_status = parsed

        if latest_bt_error is None and event in {
            "BT_ERROR",
            "BT_STOPPED_ON_FAILURE",
            "BT_BOOTSTRAP_FAILURE",
            "SEND_QUERY_ERROR",
            "ERROR",
        }:
            latest_bt_error = parsed

    # Use the latest USER_PROMPT as "What I understood"
    # For now this repeats the raw user command since the log does not yet contain a parsed intent field
    # classify_prompt fills the remaining dashboard cards based on keyword matching
    if latest_prompt:
        state["timestamp"] = latest_prompt["timestamp"]
        state["understood"] = latest_prompt["message"]
        state["raw_event"] = latest_prompt["event"]
        state["raw_message"] = latest_prompt["message"]
        state.update(classify_prompt(latest_prompt["message"]))

    # If a tool was started, show it as the current action in the "Currently doing" field
    if latest_tool_start:
        state["status"] = f'Tool running: {latest_tool_start["message"]}'
        state["source"] = "LLM / tool layer"

    # Use the LLM final response as the outcome explanation if available
    if latest_final_response:
        state["outcome"] = latest_final_response["message"]

     # BT status overrides the keyword-based state with real execution information from the robot
    if latest_bt_status:
        fields = latest_bt_status.get("fields", {})
        state["system_state"] = fields.get("system_state", state["system_state"])
        state["source"] = f'BT / {fields.get("source_component", "bt")}'
        state["status"] = (
            f'BT status: {fields.get("bt_status", "UNKNOWN")}'
            + (f' | active node: {fields.get("active_node", "")}' if fields.get("active_node") else "")
        )

    # Errors from BT or agent layer override the outcome field and set system state to failed
    if latest_bt_error:
        if latest_bt_error["event"].startswith("BT_"):
            fields = latest_bt_error.get("fields", {})
            reason = fields.get("failure_reason", latest_bt_error["message"])
            if reason:
                state["outcome"] = reason
            state["system_state"] = "failed"
            state["source"] = "Behavior Tree"
        else:
            if latest_bt_error["message"]:
                state["outcome"] = latest_bt_error["message"]
            state["system_state"] = "failed"
            state["source"] = "LLM / agent layer"

    return state


# Serves the main dashboard HTML page
@app.route("/")
def home():
    return render_template("index.html")


# API endpoint polled every 2 seconds by the frontend to get the latest dashboard data
@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(parse_current_log())


if __name__ == "__main__":
    app.run(debug=True)