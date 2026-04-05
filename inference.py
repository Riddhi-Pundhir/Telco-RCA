"""
inference.py — Telco-RCA baseline inference script.

Runs a heuristic + LLM agent against all three tasks and emits structured
[START] / [STEP] / [END] logs as required by the hackathon spec.

Usage:
    python inference.py

Environment variables:
    API_BASE_URL   LLM endpoint  (default: https://api.anthropic.com)
    MODEL_NAME     Model string  (default: claude-sonnet-4-20250514)
    HF_TOKEN       API key
"""

import json
import os
import sys
import time
import re
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.anthropic.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "claude-sonnet-4-20250514")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")

# Server (local for testing; swap for HF Space URL in prod)
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:7860")

client = OpenAI(api_key=HF_TOKEN or "placeholder", base_url=API_BASE_URL)

# ── HTTP helpers (use requests so we don't need httpx) ───────────────────────
import urllib.request

def _post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        f"{SERVER_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{SERVER_URL}{path}", timeout=10) as r:
        return json.loads(r.read())

# ── LLM agent ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert 5G network engineer specialising in Root Cause Analysis (RCA).
You are given a set of active alarms from a 5G network. Your job is to identify the single root cause
node — the one failed piece of equipment whose failure is responsible for all the downstream alarms.

Network layers (from root to leaf):
  power_unit → core_switch → radio_controller → cell_tower

Key insight: When a parent node fails, ALL its children generate symptom alarms. The real fault is
the highest-layer node that is actually broken.

Actions available:
  CHECK_LOGS <node_id>     — read error logs for a node (costs 1 step, gives clues)
  CHECK_VOLTAGE <node_id>  — measure voltage (low voltage = hardware fault)
  RESTART <node_id>        — restart a node (fixes network IF it's the root cause; false positive penalty if not)
  DIAGNOSE <node_id>       — declare a node as root cause without restarting

Strategy:
1. Group alarms by layer. If ALL towers in a region are down, suspect their shared radio controller.
2. CHECK_VOLTAGE the suspected parent first — voltage drop is a smoking gun.
3. Walk UP the tree (tower → RC → switch → power) until you find the broken node.
4. Use DIAGNOSE when confident, RESTART only when very certain.

Respond with exactly one JSON object:
{"action_type": "CHECK_LOGS"|"CHECK_VOLTAGE"|"RESTART"|"DIAGNOSE", "target_node_id": "<node_id>"}
"""

def llm_decide(obs: dict, history: list[dict]) -> dict:
    """Ask the LLM what to do next. Returns an action dict."""
    alarm_summary = []
    for a in obs.get("active_alarms", [])[:20]:  # cap context
        alarm_summary.append(f"  [{a['severity']}] {a['node_id']} ({a['layer']}): {a['message']}")

    user_msg = f"""Active alarms ({obs['total_alarm_count']} total, showing first {len(alarm_summary)}):
{chr(10).join(alarm_summary) if alarm_summary else "  (none)"}

Steps remaining: {obs['steps_remaining']}
False positives so far: {obs['false_positives_so_far']}
Nodes already checked: {obs['checked_nodes']}

Recent actions:
{json.dumps(history[-5:], indent=2) if history else "  (none)"}

What is your next action? Respond with ONLY a JSON object."""

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=200,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    # Strip markdown fences if present
    raw = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        action = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: pick the first unchecked node from alarms
        alarms = obs.get("active_alarms", [])
        checked = set(obs.get("checked_nodes", []))
        candidate = next((a["node_id"] for a in alarms if a["node_id"] not in checked), None)
        if candidate:
            action = {"action_type": "CHECK_LOGS", "target_node_id": candidate}
        else:
            action = {"action_type": "DIAGNOSE", "target_node_id": alarms[0]["node_id"] if alarms else "UNKNOWN"}
    return action


# ── Episode runner ─────────────────────────────────────────────────────────────

def run_episode(task: str) -> dict:
    """Run one full episode. Returns trajectory summary for grading."""
    obs = _post("/reset", {"task": task})

    history   = []
    step_num  = 0
    done      = False
    total_reward = 0.0
    root_cause_fixed   = False
    correct_diagnosis  = False
    false_positives    = 0
    start_time = time.time()

    while not done and step_num < 60:
        step_num += 1
        action = llm_decide(obs, history)

        result = _post("/step", {"task": task, "action": action})
        reward    = result["reward"]
        done      = result["done"]
        info      = result.get("info", {})
        obs       = result["observation"]

        total_reward += reward
        false_positives = obs.get("false_positives_so_far", 0)

        if info.get("result") == "ROOT_CAUSE_FIXED":
            root_cause_fixed = True
        if info.get("result") == "CORRECT_DIAGNOSIS":
            correct_diagnosis = True

        history.append({"step": step_num, "action": action, "reward": reward, "info": info})

        log_step(task, step_num, action, reward, info, obs)

    env_state = _get(f"/state?task={task}")
    elapsed = round(time.time() - start_time, 2)

    return {
        "task": task,
        "steps_taken": step_num,
        "total_reward": round(total_reward, 4),
        "root_cause_fixed": root_cause_fixed,
        "correct_diagnosis": correct_diagnosis,
        "false_positives": false_positives,
        "elapsed_seconds": elapsed,
        "root_cause_id": env_state.get("root_cause_id"),
    }


# ── Structured logging (mandatory hackathon format) ────────────────────────────

def log_step(task, step_num, action, reward, info, obs):
    print(json.dumps({
        "log_type": "STEP",
        "task": task,
        "step": step_num,
        "action_type": action.get("action_type"),
        "target_node": action.get("target_node_id"),
        "reward": reward,
        "done": obs.get("episode_done", False),
        "info": info,
    }), flush=True)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    tasks = ["easy", "medium", "hard"]
    results = []

    print(json.dumps({"log_type": "START", "tasks": tasks, "model": MODEL_NAME}), flush=True)

    for task in tasks:
        print(json.dumps({"log_type": "STEP", "event": "episode_start", "task": task}), flush=True)
        trajectory = run_episode(task)

        # Grade via server
        grade_resp = _post("/grade", {"task": task, "trajectory": trajectory})
        score = grade_resp["score"]
        trajectory["score"] = score
        results.append(trajectory)

        print(json.dumps({
            "log_type": "STEP",
            "event": "episode_end",
            "task": task,
            "score": score,
            "steps_taken": trajectory["steps_taken"],
            "false_positives": trajectory["false_positives"],
            "root_cause_id": trajectory["root_cause_id"],
        }), flush=True)

    avg_score = round(sum(r["score"] for r in results) / len(results), 4)

    print(json.dumps({
        "log_type": "END",
        "results": results,
        "average_score": avg_score,
        "model": MODEL_NAME,
    }), flush=True)

    return avg_score


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score > 0 else 1)
