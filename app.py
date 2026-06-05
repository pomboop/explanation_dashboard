from flask import Flask, jsonify, render_template   # CHANGED: added jsonify
from pathlib import Path                            # NEW: used to locate interaction_log.txt
import re                                           # NEW: used to parse log lines
import shlex                                        # NEW: used to parse BT key="value" log fields safely


app = Flask(__name__)                               # KEEP: same Flask app setup


# =========================
# NEW: log file setup
# =========================
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "interaction_log.txt"


# NEW: prefix pattern for parsing the common start of each log line
# This supports both:
# 2025-06-18 09:12:21 - INFO - USER_PROMPT: takeoff
# and
# 2025-06-18 09:12:21 - INFO - BT_STATUS source_component="bt" bt_name="simple_bt" ...
LOG_PREFIX_RE = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - '
    r'(?P<level>[A-Z]+) - '
    r'(?P<payload>.*)$'
)


# NEW: keyword groups for quick classification
MOVEMENT_KEYWORDS = [
    "takeoff", "take off", "land", "move", "turn", "rotate", "forward",
    "backward", "backwards", "left", "right", "up", "down", "flip"
]
TRACKING_KEYWORDS = ["track", "follow", "tracking"]
STATUS_KEYWORDS = ["status", "state"]
BATTERY_KEYWORDS = ["battery"]


# NEW: default data returned if log is empty or missing
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


# NEW: clean weird terminal characters from log text
def clean_message(message: str) -> str:
    text = (message or "").strip()
    text = text.replace("\x1b[A", "").replace("\x1b[D", "").strip()
    return " ".join(text.split())


# NEW: parse BT-style key="value" parts safely
# Example input:
# source_component="bt" bt_name="simple_bt" bt_status="RUNNING"
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


# NEW: parse a raw log line into structured fields
# Supports both old style:
# USER_PROMPT: takeoff
# and new BT style:
# BT_STATUS source_component="bt" bt_name="simple_bt" ...
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

    # OLD STYLE: EVENT: message
    if ": " in payload:
        event, message = payload.split(": ", 1)
        parsed["event"] = event.strip()
        parsed["message"] = clean_message(message)
        return parsed

    # NEW BT STYLE: EVENT key="value" key2="value2"
    parts = payload.split(" ", 1)
    parsed["event"] = parts[0].strip()

    if len(parts) > 1:
        parsed["fields"] = parse_kv_message(parts[1])
        parsed["message"] = clean_message(parts[1])

    return parsed


# NEW: basic rule-based classification of the command
# NOTE: this is only for status/outcome, not for rewriting "understood"
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


# NEW: convert numeric battery into label
# Full >= 70, Medium >= 30, Low < 30
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


# NEW: search log for battery values if they exist
# Supports old style BATTERY_UPDATE: robot=tello, percent=83.0
# and future field-based logs like battery_percent="83"
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


# NEW: get recent meaningful entries for the recent log panel
# CHANGED: this now supports both agent logs and BT logs
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
        }:
            continue

        display_message = parsed["message"]

        # NEW: make BT status lines cleaner in the dashboard
        if event == "BT_STATUS":
            fields = parsed.get("fields", {})
            display_message = (
                f'bt_status={fields.get("bt_status", "UNKNOWN")}, '
                f'system_state={fields.get("system_state", "unknown")}, '
                f'active_node={fields.get("active_node", "")}'
            )

        # NEW: show failure reason more clearly for BT errors
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


# NEW: main function that turns interaction_log.txt into dashboard JSON
def parse_current_log():
    state = default_state()

    # NEW: if the log file is missing, return safe fallback data
    if not LOG_FILE.exists():
        state["outcome"] = "interaction_log.txt was not found next to app.py."
        return state

    raw_lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    lines = [line for line in raw_lines if line.strip()]

    # NEW: fill battery and recent log list
    state["battery"] = extract_battery(lines)
    state["battery_label"] = battery_label_from_value(state["battery"])
    state["recent_entries"] = extract_recent_entries(lines)

    # NEW: collect latest relevant events from both old and new log formats
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

    # NEW: use latest USER_PROMPT as the current understood command
    if latest_prompt:
        state["timestamp"] = latest_prompt["timestamp"]

        # CHANGED ON PURPOSE:
        # For now, "What I understood" repeats exactly what the user said,
        # because the current log only gives us USER_PROMPT and not a richer parsed intent.
        state["understood"] = latest_prompt["message"]

        # KEEP / NEW COMBO:
        # We still classify the prompt to fill the other dashboard cards.
        state["raw_event"] = latest_prompt["event"]
        state["raw_message"] = latest_prompt["message"]
        state.update(classify_prompt(latest_prompt["message"]))

    # NEW: if there is a tool currently/last started, show that as status
    if latest_tool_start:
        state["status"] = f'Tool running: {latest_tool_start["message"]}'
        state["source"] = "LLM / tool layer"

    # NEW: if there is a final response, use it as outcome text
    if latest_final_response:
        state["outcome"] = latest_final_response["message"]

    # NEW: BT status can override generic rule-based state with real execution-side info
    if latest_bt_status:
        fields = latest_bt_status.get("fields", {})
        state["system_state"] = fields.get("system_state", state["system_state"])
        state["source"] = f'BT / {fields.get("source_component", "bt")}'
        state["status"] = (
            f'BT status: {fields.get("bt_status", "UNKNOWN")}'
            + (f' | active node: {fields.get("active_node", "")}' if fields.get("active_node") else "")
        )

    # NEW: explicit BT/agent errors should override a generic outcome
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


# KEEP: main page route
@app.route("/")
def home():
    return render_template("index.html")


# NEW: JSON endpoint used by the frontend in log mode
@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(parse_current_log())


if __name__ == "__main__":
    app.run(debug=True)