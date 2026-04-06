export const TASK_METADATA = {
  easy: {
    index: 1,
    title: "Alarm Containment",
    shortLabel: "Easy",
    operatorStory: "Single-site isolation",
    accent: "from-healthy/30 via-sand/10 to-transparent",
  },
  medium: {
    index: 2,
    title: "Regional Cascade",
    shortLabel: "Medium",
    operatorStory: "Cross-cluster correlation",
    accent: "from-suspect/30 via-sand/10 to-transparent",
  },
  hard: {
    index: 3,
    title: "Systemic Outage",
    shortLabel: "Hard",
    operatorStory: "Multi-region graph traversal",
    accent: "from-failure/30 via-sand/10 to-transparent",
  },
};

export const ACTION_LABELS = {
  CHECK_LOGS: "Query Node",
  CHECK_VOLTAGE: "Check Voltage",
  TRACE_PATH: "Trace Path",
  RESTART: "Restart Node",
  DIAGNOSE: "Submit RCA",
};

export const ACTION_API_NAMES = {
  CHECK_LOGS: "query_node",
  CHECK_VOLTAGE: "check_voltage",
  TRACE_PATH: "trace_path",
  RESTART: "restart_node",
  DIAGNOSE: "submit_root_cause",
};

export const SEVERITY_WEIGHT = {
  MINOR: 0.32,
  WARNING: 0.56,
  MAJOR: 0.82,
  CRITICAL: 1,
};

export const STATUS_COLORS = {
  UP: "healthy",
  DEGRADED: "suspect",
  FAILED: "failure",
};

export const LAYER_CONFIG = {
  power_unit: {
    label: "Power Unit",
    shortLabel: "PWR",
    role: "Power Hub",
    tint: "#D7B79B",
  },
  core_switch: {
    label: "BBU",
    shortLabel: "BBU",
    role: "Backhaul Switch",
    tint: "#E8D1C5",
  },
  radio_controller: {
    label: "RRU",
    shortLabel: "RRU",
    role: "Radio Controller",
    tint: "#F2B950",
  },
  cell_tower: {
    label: "Antenna",
    shortLabel: "ANT",
    role: "Sector Endpoint",
    tint: "#F3E8DF",
  },
};

export const MANUAL_ACTIONS = [
  "CHECK_LOGS",
  "CHECK_VOLTAGE",
  "TRACE_PATH",
  "RESTART",
  "DIAGNOSE",
];

