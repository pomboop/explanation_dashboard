// Mock scenarios simulating what the LLM explanation layer would generate per persona and detail level
// Each scenario has neutral/friendly/expert personas and brief/normal/detailed levels
// This is the demo layer used in mock mode; the LLM will replace this in the full version
const scenarios = {
  follow: {
    understood: {
      neutral: {
        brief: "Follow nearest person.",
        normal: "Task: follow the nearest detected person.",
        detailed:
          "Task: follow the nearest detected person based on current visual detection input.",
      },
      friendly: {
        brief: "Okay! I'll follow you.",
        normal: "Got it! I'll follow you wherever you go.",
        detailed:
          "Got it! I understood that you want me to follow you, so I'll keep tracking the nearest visible person.",
      },
      expert: {
        brief: "Intent: PersonFollowing.",
        normal: "Parsed intent: PersonFollowing. Target: nearest bounding box.",
        detailed:
          "Parsed intent: PersonFollowing. Target selection: nearest detected bounding box. Command confidence: 0.97.",
      },
    },
    status: {
      neutral: {
        brief: "Tracking person.",
        normal: "Running: tracking person in camera frame.",
        detailed:
          "Running: tracking the detected person in the camera frame and updating target position continuously.",
      },
      friendly: {
        brief: "Following now!",
        normal: "I'm on it — following you right now!",
        detailed:
          "I'm on it — I'm following you right now and keeping you centered in my view.",
      },
      expert: {
        brief: "TrackTarget active.",
        normal: "BT node active: TrackTarget. Input: /camera/rgb.",
        detailed:
          "BT node active: TrackTarget. Input stream: /camera/rgb. Detection pipeline active. Tracking updates are running.",
      },
    },
    outcome: {
      neutral: {
        brief: "No issues.",
        normal: "Task running normally. No issues.",
        detailed:
          "Task is running normally. No execution issue has been reported so far.",
      },
      friendly: {
        brief: "All good!",
        normal: "Everything looks good so far!",
        detailed:
          "Everything looks good so far — I'm following successfully without any problems.",
      },
      expert: {
        brief: "RUNNING.",
        normal: "Node status: RUNNING. No exception raised.",
        detailed:
          "Node status: RUNNING. No exception raised. Tracking pipeline stable and frame processing is within expected bounds.",
      },
    },
    state: "running",
    source: "Mock scenario",
  },

  navigate: {
    understood: {
      neutral: {
        brief: "Go to kitchen.",
        normal: "Task: navigate to the kitchen.",
        detailed:
          "Task: navigate to the kitchen using the current mapped environment.",
      },
      friendly: {
        brief: "Heading to kitchen!",
        normal: "Sure! Heading to the kitchen now.",
        detailed:
          "Sure! I understood that you want me to go to the kitchen, so I'm starting navigation now.",
      },
      expert: {
        brief: "Intent: NavigateTo.",
        normal: "Parsed intent: NavigateTo. Target location: kitchen.",
        detailed:
          "Parsed intent: NavigateTo. Target location: kitchen. Semantic map lookup completed successfully.",
      },
    },
    status: {
      neutral: {
        brief: "Planning route.",
        normal: "Running: path planning and movement.",
        detailed:
          "Running: computing a path and executing motion toward the requested destination.",
      },
      friendly: {
        brief: "Finding the route!",
        normal: "I'm finding the best route to the kitchen!",
        detailed:
          "I'm finding the best route to the kitchen and moving there step by step.",
      },
      expert: {
        brief: "MoveToGoal active.",
        normal: "BT node active: MoveToGoal. Planner: NavStack2.",
        detailed:
          "BT node active: MoveToGoal. Planner: NavStack2. Goal pose resolved and navigation has started.",
      },
    },
    outcome: {
      neutral: {
        brief: "No issues.",
        normal: "Navigation in progress. No issues.",
        detailed:
          "Navigation is currently in progress and no obstacle or planner error has been reported.",
      },
      friendly: {
        brief: "Moving smoothly!",
        normal: "Almost there, moving smoothly!",
        detailed:
          "Everything is going well — I'm moving smoothly toward the kitchen.",
      },
      expert: {
        brief: "Planner OK.",
        normal: "Costmap clear. No obstacle detected.",
        detailed:
          "Costmap clear. Local planner active. No obstacle detected and the route remains valid.",
      },
    },
    state: "running",
    source: "Mock scenario",
  },

  success: {
    understood: {
      neutral: {
        brief: "Command completed.",
        normal: "Task completed successfully.",
        detailed:
          "The requested task was understood correctly and has now completed successfully.",
      },
      friendly: {
        brief: "Done!",
        normal: "Done! I finished the task successfully.",
        detailed:
          "Done! I understood your request and completed it successfully.",
      },
      expert: {
        brief: "Execution complete.",
        normal: "Execution complete. Goal reached successfully.",
        detailed:
          "Execution complete. Goal state reached successfully with no failure reported by the active behavior nodes.",
      },
    },
    status: {
      neutral: {
        brief: "Task finished.",
        normal: "Status: task finished.",
        detailed:
          "Status: the active task has finished and no further action is currently being executed.",
      },
      friendly: {
        brief: "I finished it!",
        normal: "I finished it successfully!",
        detailed:
          "I finished the task successfully and I'm now waiting for the next command.",
      },
      expert: {
        brief: "BT returned SUCCESS.",
        normal: "BT node returned SUCCESS.",
        detailed:
          "BT execution completed with return status SUCCESS. Final node terminated normally.",
      },
    },
    outcome: {
      neutral: {
        brief: "Success.",
        normal: "Outcome: success. No issues reported.",
        detailed:
          "Outcome: success. The system completed the requested task without reporting any issue.",
      },
      friendly: {
        brief: "Everything worked!",
        normal: "Everything worked as expected!",
        detailed:
          "Everything worked as expected — the task finished cleanly with no problem.",
      },
      expert: {
        brief: "SUCCESS.",
        normal: "Execution result: SUCCESS. No exception raised.",
        detailed:
          "Execution result: SUCCESS. No exception raised. Final completion state verified.",
      },
    },
    state: "success",
    source: "Mock scenario",
  },

  fail: {
    understood: {
      neutral: {
        brief: "Follow nearest person.",
        normal: "Task: follow the nearest detected person.",
        detailed:
          "Task: follow the nearest detected person based on current camera input.",
      },
      friendly: {
        brief: "I'll try to follow you.",
        normal: "Got it! I'll try to follow you.",
        detailed:
          "Got it! I understood that you want me to follow you, so I tried to start tracking.",
      },
      expert: {
        brief: "Intent: PersonFollowing.",
        normal: "Parsed intent: PersonFollowing. Target: nearest bounding box.",
        detailed:
          "Parsed intent: PersonFollowing. Target selection: nearest bounding box. Command confidence: 0.97.",
      },
    },
    status: {
      neutral: {
        brief: "Detection failed.",
        normal: "Failed: could not detect a person.",
        detailed:
          "Failed: the system could not detect a valid person target in the current camera frame.",
      },
      friendly: {
        brief: "I couldn't find anyone.",
        normal: "Oops — I couldn't find anyone to follow!",
        detailed:
          "Oops — I tried to follow, but I couldn't find anyone clearly enough to track.",
      },
      expert: {
        brief: "PersonDetection failed.",
        normal: "BT node failed: PersonDetection. Return status: FAILURE.",
        detailed:
          "BT node failed: PersonDetection. Return status: FAILURE. No stable target satisfied the detection threshold.",
      },
    },
    outcome: {
      neutral: {
        brief: "No person detected.",
        normal: "Issue: no person detected in camera frame.",
        detailed:
          "Issue explanation: no person was detected in the camera frame, so the follow task could not continue.",
      },
      friendly: {
        brief: "I couldn't spot anyone.",
        normal: "I looked around but couldn't spot anyone nearby.",
        detailed:
          "I looked around but couldn't spot anyone nearby. You could try moving closer or standing more clearly in view.",
      },
      expert: {
        brief: "Detection threshold not met.",
        normal: "Exception: detection confidence below threshold.",
        detailed:
          "Exception: DetectionNode returned no valid target. YOLO confidence stayed below threshold, so execution stopped.",
      },
    },
    state: "failed",
    source: "Mock scenario",
  },

  reset: {
    understood: {
      neutral: {
        brief: "Waiting for command...",
        normal: "Waiting for command...",
        detailed: "Waiting for command...",
      },
      friendly: {
        brief: "Waiting for command...",
        normal: "Waiting for command...",
        detailed: "Waiting for command...",
      },
      expert: {
        brief: "Waiting for command...",
        normal: "Waiting for command...",
        detailed: "Waiting for command...",
      },
    },
    status: {
      neutral: { brief: "Idle", normal: "Idle", detailed: "Idle" },
      friendly: { brief: "Idle", normal: "Idle", detailed: "Idle" },
      expert: { brief: "Idle", normal: "Idle", detailed: "Idle" },
    },
    outcome: {
      neutral: {
        brief: "No issues reported.",
        normal: "No issues reported.",
        detailed: "No issues reported.",
      },
      friendly: {
        brief: "No issues reported.",
        normal: "No issues reported.",
        detailed: "No issues reported.",
      },
      expert: {
        brief: "No issues reported.",
        normal: "No issues reported.",
        detailed: "No issues reported.",
      },
    },
    state: "idle",
    source: "Mock scenario",
  },
};

// Default mode is log mode so the dashboard reads real data on startup
let currentMode = "log";
let currentPersona = "neutral";
let currentDetail = "normal";
let currentScenario = "reset";

// Timer reference for the polling interval that refreshes the dashboard every 2 seconds
let refreshTimer = null;

function titleCase(text) {
  if (!text) return "Idle";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function getCurrentTime() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

function applyStateClasses(state) {
  const stateEl = document.getElementById("system-state");
  const statusCard = document.getElementById("card-status");
  const outcomeCard = document.getElementById("card-outcome");
  const dot = document.getElementById("status-dot");

  stateEl.textContent = titleCase(state);
  stateEl.className = "meta-value state-badge";
  statusCard.className = "card";
  outcomeCard.className = "card";
  dot.className = "status-indicator";

  if (state === "running") {
    stateEl.classList.add("running");
    statusCard.classList.add("active");
    dot.classList.add("running");
  } else if (state === "success") {
    stateEl.classList.add("success");
    statusCard.classList.add("success");
    outcomeCard.classList.add("success");
    dot.classList.add("success");
  } else if (state === "failed") {
    stateEl.classList.add("failed");
    statusCard.classList.add("error");
    outcomeCard.classList.add("error");
    dot.classList.add("error");
  } else {
    stateEl.classList.add("idle");
    dot.classList.add("idle");
  }
}

// Applies color class to the battery badge based on Full / Medium / Low / Unknown label
function applyBatteryClass(label) {
  const batteryEl = document.getElementById("battery-text");
  batteryEl.className = "meta-value battery-badge";

  if (label === "Full") {
    batteryEl.classList.add("full");
  } else if (label === "Medium") {
    batteryEl.classList.add("medium");
  } else if (label === "Low") {
    batteryEl.classList.add("low");
  } else {
    batteryEl.classList.add("unknown");
  }
}

// Shows the simulator panel only in mock mode, hides it in log mode
function setSimulatorVisibility() {
  const simulatorPanel = document.getElementById("simulator-panel");
  simulatorPanel.style.display = currentMode === "mock" ? "flex" : "none";
}

// Renders the recent log activity list from the entries returned by the Flask API
function renderRecentLog(entries) {
  const list = document.getElementById("recent-log-list");

  if (!entries || entries.length === 0) {
    list.innerHTML = '<li class="log-empty">No log entries available.</li>';
    return;
  }

  list.innerHTML = entries
    .map(
      (entry) => `
    <li class="log-item">
      <span class="log-time">${entry.timestamp}</span>
      <span class="log-message">${entry.message}</span>
    </li>
  `,
    )
    .join("");
}

// Updates all dashboard fields from a payload object (from Flask API or mock scenario)
function renderState(payload) {
  document.getElementById("understood-text").textContent =
    payload.understood || "Waiting for command...";
  document.getElementById("status-text").textContent = payload.status || "Idle";
  document.getElementById("outcome-text").textContent =
    payload.outcome || "No issues reported.";
  document.getElementById("battery-text").textContent =
    payload.battery_label || payload.battery || "Unknown";
  document.getElementById("source-text").textContent = payload.source || "—";
  document.getElementById("timestamp-text").textContent =
    payload.timestamp || "—";

  applyStateClasses(payload.system_state || payload.state || "idle");
  applyBatteryClass(payload.battery_label || "Unknown");
  renderRecentLog(payload.recent_entries || []);
}

function displayScenario(name) {
  const scenario = scenarios[name];
  const persona = currentPersona;
  const detail = currentDetail;

  renderState({
    system_state: scenario.state,
    source: scenario.source,
    timestamp: getCurrentTime(),
    // Mock scenarios have no real battery data so battery stays Unknown
    battery: "Unknown",
    battery_label: "Unknown",
    understood: scenario.understood[persona][detail],
    status: scenario.status[persona][detail],
    outcome: scenario.outcome[persona][detail],
    // Single fake log entry shown in the activity panel during mock mode
    recent_entries: [
      { timestamp: getCurrentTime(), message: `Mock scenario: ${name}` },
    ],
  });
}

function updatePersona() {
  currentPersona = document.getElementById("persona").value;
  if (currentMode === "mock") {
    displayScenario(currentScenario);
  }
}

function updateDetailLevel() {
  currentDetail = document.getElementById("detail").value;
  if (currentMode === "mock") {
    displayScenario(currentScenario);
  }
}

function simulateScenario(name) {
  currentScenario = name;
  if (currentMode === "mock") {
    displayScenario(name);
  }
}

// Fetches the latest dashboard data from Flask and updates all fields
async function refreshDashboardFromLog() {
  try {
    const response = await fetch("/api/dashboard", { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    renderState(data);
  } catch (error) {
    renderState({
      system_state: "failed",
      source: "Log mode",
      timestamp: getCurrentTime(),
      battery: "Unknown",
      battery_label: "Unknown",
      understood: "Could not read the log file.",
      status: "Log refresh failed.",
      outcome: `Dashboard refresh failed: ${error.message}`,
      recent_entries: [],
    });
  }
}

// Starts or restarts the 2-second polling interval for log mode
function restartPolling() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }

  if (currentMode !== "log") {
    return;
  }

  refreshTimer = setInterval(refreshDashboardFromLog, 2000);
}

function updateMode() {
  currentMode = document.getElementById("data-mode").value;
  setSimulatorVisibility();

  if (currentMode === "mock") {
    displayScenario(currentScenario);
  } else {
    refreshDashboardFromLog();
  }

  restartPolling();
}

// Initialize the dashboard on page load: start in log mode and begin polling
setSimulatorVisibility();
refreshDashboardFromLog();
restartPolling();
