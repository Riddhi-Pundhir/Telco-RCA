"""
inference.py — Telco-RCA baseline inference script.

Runs a heuristic + LLM agent against all three tasks (easy, medium, hard)
and emits structured [START] / [STEP] / [END] logs as required by the spec.

The agent uses a sophisticated top-down diagnosis strategy:
  1. Analyse the alarm landscape — group by layer, region, parent
  2. Identify the "cone of failure" — which subtree is impacted
  3. Walk upward from leaf alarms to find the highest-layer failing node
  4. CHECK_VOLTAGE suspected root nodes (voltage drop = smoking gun)
  5. Use TRACE_PATH to confirm parent–child relationships
  6. RESTART (confident) or DIAGNOSE (safe) the root cause

Usage:
    python inference.py

Environment variables:
    API_BASE_URL   LLM endpoint  (default: https://api.anthropic.com/v1)
    MODEL_NAME     Model string  (default: claude-sonnet-4-20250514)
    HF_TOKEN       API key
"""

import json
import os
import sys
import time
import re
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.anthropic.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "claude-sonnet-4-20250514")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")

# Server (local for testing; swap for HF Space URL in prod)
SERVER_URL = os.environ.get("SERVER_URL", "https://ayushman098-telco-rca.hf.space/")

client = OpenAI(api_key=HF_TOKEN or "placeholder", base_url=API_BASE_URL)

# ── HTTP helpers ──────────────────────────────────────────────────────
import urllib.request


def _post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    url = f"{SERVER_URL.rstrip('/')}/{path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _get(path: str) -> dict:
    url = f"{SERVER_URL.rstrip('/')}/{path.lstrip('/')}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


# ── LLM Agent ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert 5G network engineer specialising in Root Cause Analysis (RCA).
You are given a set of active alarms from a 5G network. Your job is to identify the single root
cause node — the one failed piece of equipment whose failure is responsible for all downstream alarms.

## Network Topology (layers from root to leaf):
  power_unit → core_switch → radio_controller → cell_tower

## Key Insight:
When a parent node fails, ALL its children generate symptom alarms. The real fault is the
HIGHEST-layer node that is actually broken. Downstream alarms are just symptoms.

## Node ID Naming Convention:
  PWR_XXX           — Power Units (layer 0, roots)
  SW_XX_XX          — Core Switches (layer 1, children of PWR)
  RC_XX_XX_XX       — Radio Controllers (layer 2, children of SW)
  TOWER_XX_XX_XX_XX — Cell Towers (layer 3, leaves)

## Actions Available:
  CHECK_LOGS <node_id>    — Read error logs (costs 1 step, gives status + textual clues)
  CHECK_VOLTAGE <node_id> — Measure voltage (low voltage = hardware fault, CRITICAL if < 30V)
  TRACE_PATH <node_id>    — Show full path from node up to tree root + direct children with status
  RESTART <node_id>       — Fix the network IF it's the root cause (+reward), else FALSE POSITIVE (-0.3)
  DIAGNOSE <node_id>      — Declare root cause without restarting (safer, lower max reward)

## Strategy:
1. Examine the alarms. Group them by their node prefixes to identify affected subtrees.
2. From node IDs, infer the parent hierarchy:
   - TOWER_01_02_03_00 is a child of RC_01_02_03
   - RC_01_02_03 is a child of SW_01_02
   - SW_01_02 is a child of PWR_001 (approximately PWR_0XX where XX = first digits)
3. CHECK_VOLTAGE on the suspected root node — voltage < 30V confirms hardware fault.
4. If a power unit's voltage is CRITICAL, that's almost certainly the root cause.
5. Use TRACE_PATH to confirm parent relationships when unsure.
6. Use DIAGNOSE when fairly confident, RESTART only when very certain.
7. Be EFFICIENT — minimize wasted steps. Every false restart is heavily penalized.

## Response Format:
Respond with EXACTLY one JSON object, nothing else:
{"action_type": "CHECK_LOGS"|"CHECK_VOLTAGE"|"RESTART"|"DIAGNOSE"|"TRACE_PATH", "target_node_id": "<node_id>"}
"""


def llm_decide(obs: dict, history: list[dict]) -> dict:
    """Ask the LLM what to do next. Returns an action dict."""
    alarm_summary = []
    for a in obs.get("active_alarms", [])[:30]:  # show more context
        alarm_summary.append(
            f"  [{a['severity']}] {a['node_id']} ({a['layer']}): {a['message']}"
        )

    # Network summary context
    net_summary = obs.get("network_summary", {})
    layers_info = net_summary.get("layers", {})
    regions_info = net_summary.get("regions", {})

    layer_str = "\n".join(
        f"  {layer}: {info['alarming']}/{info['total']} alarming"
        for layer, info in layers_info.items()
    )
    region_str = "\n".join(
        f"  {region}: {info['alarming_nodes']}/{info['total_nodes']} alarming"
        for region, info in regions_info.items()
    )

    user_msg = f"""Active alarms ({obs['total_alarm_count']} total, showing first {len(alarm_summary)}):
{chr(10).join(alarm_summary) if alarm_summary else "  (none)"}

Network Layer Summary:
{layer_str or "  (unavailable)"}

Region Summary:
{region_str or "  (unavailable)"}

Steps remaining: {obs['steps_remaining']}
False positives so far: {obs['false_positives_so_far']}
Nodes already checked: {obs['checked_nodes']}

Recent actions and results:
{json.dumps(history[-5:], indent=2) if history else "  (none)"}

What is your next action? Respond with ONLY a JSON object."""

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=300,
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown fences if present
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        action = json.loads(raw)
    except Exception:
        # Fallback: heuristic strategy
        action = _heuristic_fallback(obs, history)

    return action


def _heuristic_fallback(obs: dict, history: list[dict]) -> dict:
    """
    Deterministic heuristic when LLM fails.
    Strategy: extract parent IDs from alarm node IDs, walk up to power units.
    """
    alarms = obs.get("active_alarms", [])
    checked = set(obs.get("checked_nodes", []))

    # Extract candidate parent nodes from alarm node IDs
    parent_candidates = set()
    for a in alarms:
        nid = a["node_id"]
        if nid.startswith("TOWER_"):
            # Parent is radio controller: TOWER_XX_XX_XX_YY → RC_XX_XX_XX
            parts = nid[6:]  # strip "TOWER_"
            rc_parts = "_".join(parts.split("_")[:-1])
            parent_candidates.add(f"RC_{rc_parts}")
        elif nid.startswith("RC_"):
            # Parent is core switch: RC_XX_XX_YY → SW_XX_XX
            parts = nid[3:]
            sw_parts = "_".join(parts.split("_")[:-1])
            parent_candidates.add(f"SW_{sw_parts}")
        elif nid.startswith("SW_"):
            # Parent is power unit: SW_XX_YY → PWR_0XX
            parts = nid[3:]
            pwr_idx = int(parts.split("_")[0])
            parent_candidates.add(f"PWR_{pwr_idx:03d}")

    # Also add power units directly from alarms
    for a in alarms:
        if a["node_id"].startswith("PWR_"):
            parent_candidates.add(a["node_id"])

    # Check unchecked parent candidates first (voltage check)
    unchecked_parents = parent_candidates - checked
    if unchecked_parents:
        # Prefer power units
        pwr = [p for p in unchecked_parents if p.startswith("PWR_")]
        if pwr:
            return {"action_type": "CHECK_VOLTAGE", "target_node_id": sorted(pwr)[0]}
        sw = [p for p in unchecked_parents if p.startswith("SW_")]
        if sw:
            return {"action_type": "CHECK_VOLTAGE", "target_node_id": sorted(sw)[0]}
        return {"action_type": "CHECK_VOLTAGE", "target_node_id": sorted(unchecked_parents)[0]}

    # If we've checked everything, look at history for critical voltage readings
    for h in reversed(history):
        info = h.get("info", {})
        if info.get("status") == "CRITICAL" and "node_id" in info:
            nid = info["node_id"]
            # Already tried restarting this one?
            if not any(
                hh.get("action", {}).get("target_node_id") == nid
                and hh.get("action", {}).get("action_type") in ("RESTART", "DIAGNOSE")
                for hh in history
            ):
                return {"action_type": "DIAGNOSE", "target_node_id": nid}

    # Last resort: diagnose first alarm
    if alarms:
        return {"action_type": "DIAGNOSE", "target_node_id": alarms[0]["node_id"]}

    return {"action_type": "DIAGNOSE", "target_node_id": "UNKNOWN"}


# Fixed seeds for reproducible baseline runs
TASK_SEEDS = {"easy": 42, "medium": 43, "hard": 44}


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: str | None) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def run_episode(task: str) -> float:
    """Run one full episode and emit stdout tags for OpenEnv validation."""
    seed = TASK_SEEDS.get(task, 42)
    obs = _post("/reset", {"task": task, "seed": seed})

    history = []
    rewards_list = []
    step_num = 0
    done = False
    start_time = time.time()
    
    max_steps = {"easy": 15, "medium": 30, "hard": 50}.get(task, 30)

    log_start(task=task, env="telco-rca", model=MODEL_NAME)

    info = {}
    while not done and step_num < max_steps:
        step_num += 1
        action = llm_decide(obs, history)

        # Build action string without spaces for the STDOUT log
        action_type = action.get("action_type", "")
        target_node = action.get("target_node_id", "")
        action_str = f"{action_type}('{target_node}')"

        result = _post("/step", {"task": task, "action": action})
        reward = result["reward"]
        done = result["done"]
        info = result.get("info", {})
        obs = result["observation"]

        rewards_list.append(reward)
        error_msg = info.get("error")

        history.append({
            "step": step_num,
            "action": action,
            "reward": reward,
            "info": info,
        })

        log_step(step=step_num, action=action_str, reward=reward, done=done, error=error_msg)

    # Grade the episode
    try:
        env_state = _get(f"/state?task={task}")
        trajectory = {
            "task": task,
            "steps_taken": step_num,
            "total_reward": round(sum(rewards_list), 4),
            "root_cause_fixed": bool(info.get("result") == "ROOT_CAUSE_FIXED"),
            "correct_diagnosis": bool(info.get("result") == "CORRECT_DIAGNOSIS"),
            "false_positives": obs.get("false_positives_so_far", 0),
            "elapsed_seconds": round(time.time() - start_time, 2),
            "root_cause_id": env_state.get("root_cause_id"),
            "action_log": history,
        }
        grade_resp = _post("/grade", {"task": task, "trajectory": trajectory})
        score = grade_resp.get("score", 0.0)
    except Exception as e:
        print(f"[DEBUG] Failed to grade: {e}", file=sys.stderr)
        score = 0.0

    success = score > 0.0
    log_end(success=success, steps=step_num, score=score, rewards=rewards_list)

    return score


def main():
    # The OpenEnv evaluator typically tests a specific task by setting TASK_NAME in the environment
    task = os.environ.get("TASK_NAME", "easy")
    score = run_episode(task)
    return score


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score > 0 else 1)
