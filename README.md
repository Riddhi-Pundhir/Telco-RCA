---
title: Telco-RCA
emoji: 📡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---
# 🔴 Telco-RCA — 5G Network Root Cause Analysis Environment

> **OpenEnv submission** · Team Codyy AR · April 2026 Hackathon
> 
> 🔗 **Live Dashboard:** [https://ayushman098-telco-rca.hf.space/](https://ayushman098-telco-rca.hf.space/)

An RL environment where an AI agent must diagnose cascading equipment failures in a 5G network — finding the one broken node responsible for hundreds of downstream alarms, as fast as possible, with minimum false positives.

---

## 🌐 The Problem

Modern 5G networks are massive graphs. When a **Power Unit** fails, it triggers a **cascade** — hundreds of downstream towers, radio controllers, and switches all emit alarms simultaneously. Human engineers take **hours** to find the real culprit. This environment trains agents to do it in **seconds**.

```
Power Unit  ──►  Core Switch  ──►  Radio Controller  ──►  Cell Tower
   [FAILED]         [ALARM]              [ALARM]              [ALARM]
                    [ALARM]              [ALARM]              [ALARM]
                                         [ALARM]              [ALARM]
                                                              [ALARM]
```

### Why This Is Hard for AI

- **Graph reasoning**: Must understand parent-child causality in a 500-node knowledge graph
- **Noise**: 40% of alarms in hard mode are spurious — the agent must distinguish real cascades from transients
- **Efficiency pressure**: Every wrong restart sends a field crew to the wrong cell site ($$$ penalty)
- **Scale**: Up to 300 simultaneous alarms across 5 geographic regions with 475+ edges

---

## 🗂️ Project Structure

```
telco-rca/
├── app/
│   ├── __init__.py          # Package init
│   ├── main.py              # FastAPI server (OpenEnv HTTP interface)
│   ├── environment.py       # Core simulation: topology, failures, actions
│   ├── models.py            # Pydantic models for all I/O
│   └── graders.py           # Deterministic scoring (F1 + MTTR)
├── tests/
│   ├── __init__.py
│   └── test_environment.py  # 47 unit + integration tests
├── inference.py             # LLM baseline agent script
├── openenv.yaml             # OpenEnv specification
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 🎮 Tasks

| Task | Nodes | Regions | Alarms | Noise | Max Steps | Failure Layer |
|------|-------|---------|--------|-------|-----------|---------------|
| **easy** | 20 | 1 | 5–20 | 0% | 15 | Power Unit only |
| **medium** | 100 | 3 | 10–50 | 20% | 30 | Power Unit, Core Switch |
| **hard** | 500 | 5 | 50–300 | 40% | 50 | All layers |

### Task Details

**Easy — Alarm Classification**
> A single power unit has failed. ~5-10 downstream alarms, no noise. Classify the alarm (e.g. "Mains Failure") and suggest a standard repair. Good for testing basic fault recognition.

**Medium — Multi-Alarm Correlation**
> Correlate 10+ simultaneous alarms across a 3-region cluster to find the ONE true faulty node. 20% noise alarms act as distractors. Tests alarm correlation and parent-child reasoning.

**Hard — Knowledge Graph RCA**
> Full 500-node knowledge graph traversal. Navigate physical and logical dependencies across 5 regions. 40% noise. The agent must trace the cascade upstream through layers of switches, controllers, and power units to stop a systemic outage.

---

## 🏗️ Network Topology

The simulated 5G network is a **layered directed acyclic graph**:

```
Layer 0: Power Units (PWR_XXX)           — ~25 nodes (roots, no parent)
Layer 1: Core Switches (SW_XX_XX)        — ~75 nodes (2-4 per power unit)
Layer 2: Radio Controllers (RC_XX_XX_XX) — ~250 nodes (2-5 per switch)
Layer 3: Cell Towers (TOWER_XX_XX_XX_XX) — ~150 nodes (leaf nodes)
```

Each node has:
- `node_id` — Unique identifier encoding the parent hierarchy
- `layer` — Equipment type (power_unit / core_switch / radio_controller / cell_tower)
- `parent_id` — Direct parent in the topology tree
- `children` — List of child node IDs
- `status` — UP / DEGRADED / FAILED
- `region` — Geographic region assignment
- `voltage` — Power measurement (48V nominal, <30V = hardware fault)
- `temperature_c` — Operating temperature

---

## ⚡ Actions

| Action | Cost | Effect |
|--------|------|--------|
| `CHECK_LOGS` | -0.01 | Read node error logs. Returns status, layer, parent, alarm text, uptime. |
| `CHECK_VOLTAGE` | -0.01 | Measure voltage & temperature. Low voltage (<30V) = hardware fault. |
| `TRACE_PATH` | -0.01 | Show full path from node up to tree root + direct children with status. |
| `RESTART` | -0.01 | Fix the network **if root cause** (+reward), else **false positive** (-0.3). |
| `DIAGNOSE` | -0.01 | Declare root cause without restarting (safer, lower max reward). |

### Action Strategy Guide

1. **Group alarms by layer** — if all towers in a region are down, suspect their shared radio controller
2. **Walk UP the tree** — use node ID naming convention to infer parents:
   - `TOWER_01_02_03_00` → parent RC: `RC_01_02_03`
   - `RC_01_02_03` → parent SW: `SW_01_02`
   - `SW_01_02` → parent PWR: `PWR_001`
3. **CHECK_VOLTAGE** the suspect — voltage drop < 30V is a smoking gun
4. **TRACE_PATH** to confirm parent-child relationships
5. **DIAGNOSE** when confident, **RESTART** only when very certain

---

## 📊 Reward / Grading

```
score = clamp(efficiency_mult + speed_bonus × 0.2 − fp_penalty, 0, 1)

  efficiency_mult = 1 − (steps_taken / max_steps)
  speed_bonus     = max(0, 1 − elapsed_seconds / 300)
  fp_penalty      = min(0.8, false_positives × 0.15)
```

### Metrics Breakdown

| Metric | Weight | Description |
|--------|--------|-------------|
| **F1-Score** | Primary | Precision & recall for root cause identification |
| **MTTR** | 0.2× | Mean Time to Recovery — speed bonus for fast resolution |
| **FP Penalty** | -0.15/ea | Each wrong restart/diagnosis penalised (capped at 0.8) |
| **Efficiency** | Primary | Steps used vs max allowed |

Scores are always in **[0.0, 1.0]** and are **deterministic** for a given trajectory.

### Grade Response Example

```json
{
  "score": 0.9847,
  "reason": "Root cause correctly identified.",
  "breakdown": {
    "base": 1.0,
    "f1_score": 1.0,
    "efficiency_mult": 0.8667,
    "speed_bonus": 0.198,
    "fp_penalty": 0.0,
    "precision": 1.0,
    "recall": 1.0,
    "steps_used": 2,
    "max_steps": 15,
    "elapsed_seconds": 3.0
  }
}
```

---

## 🚀 Quick Start

### Local

```bash
pip install -r requirements.txt

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 7860

# Run tests (47 tests)
python -m pytest tests/ -v

# Run baseline agent (set env vars first)
export API_BASE_URL=https://api.anthropic.com/v1
export MODEL_NAME=claude-sonnet-4-20250514
export HF_TOKEN=your_key_here
python inference.py
```

### Docker

```bash
docker build -t telco-rca .
docker run -p 7860:7860 \
  -e API_BASE_URL=https://api.anthropic.com/v1 \
  -e MODEL_NAME=claude-sonnet-4-20250514 \
  -e HF_TOKEN=your_key \
  telco-rca
```

---

## 🔌 API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check + available tasks |
| `GET` | `/tasks` | List all tasks with full metadata |
| `POST` | `/reset` | Start new episode `{"task": "easy", "seed": 42}` |
| `POST` | `/step` | Execute action `{"task": "easy", "action": {...}}` |
| `GET` | `/state` | Internal state (root cause, topology stats) |
| `POST` | `/grade` | Score a trajectory with F1 breakdown |

### Example Interaction

```bash
# 1. Reset — get initial alarm set
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "hard"}'

# 2. Trace path from alarming tower upward
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"task": "hard", "action": {"action_type": "TRACE_PATH", "target_node_id": "TOWER_09_00_03_00"}}'

# 3. Check voltage on suspected root cause
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"task": "hard", "action": {"action_type": "CHECK_VOLTAGE", "target_node_id": "RC_09_00_03"}}'

# 4. Restart the confirmed root cause
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"task": "hard", "action": {"action_type": "RESTART", "target_node_id": "RC_09_00_03"}}'

# 5. Grade the trajectory
curl -X POST http://localhost:7860/grade \
  -H "Content-Type: application/json" \
  -d '{"task": "hard", "trajectory": {"root_cause_fixed": true, "steps_taken": 3, "false_positives": 0, "elapsed_seconds": 5}}'
```

---

## 🧠 Agent Strategy (Baseline)

The LLM baseline uses a **top-down diagnosis** strategy:

1. Receive alarm landscape with layer/region summaries
2. Group active alarms by network layer — identify which subtree is affected
3. Extract parent node IDs from alarm node IDs using naming convention
4. `CHECK_VOLTAGE` the most upstream suspect (prefer power units > switches > RCs)
5. If voltage is CRITICAL (<30V), that's the root cause
6. `TRACE_PATH` to confirm parent-child relationships when ambiguous
7. `RESTART` or `DIAGNOSE` with confidence

### Heuristic Fallback

When the LLM is unavailable or returns invalid JSON, the agent falls back to:
- Extracting parent candidates from alarm node ID prefixes
- Prioritising power units, then switches, then radio controllers
- Checking voltage on each suspect in order
- Diagnosing the first node with CRITICAL voltage

---

## 🏆 Why This Environment Matters

- **Real-world gap**: Telco operators spend millions/year on manual RCA. No public RL benchmark exists for this domain.
- **Graph reasoning**: Forces agents to understand parent-child causality in a knowledge graph, not just pattern-match alarms.
- **Adversarial noise**: 40% spurious alarms in hard mode test robustness against real-world alarm fatigue.
- **MTTR metric**: Speed matters — every minute of 5G downtime costs operators ~$5,000.
- **False positive cost**: Wrong restarts waste field crew time ($500+/dispatch).
- **Scalability**: From 20-node toy networks to 500-node production-scale topologies.

---

## ⚙️ Environment Variables

```
API_BASE_URL   The LLM API endpoint (default: https://api.anthropic.com/v1)
MODEL_NAME     Model identifier for inference (default: claude-sonnet-4-20250514)
HF_TOKEN       Hugging Face / API key
SERVER_URL     Environment server URL (default: http://localhost:7860)
```

---

## 🧪 Test Coverage

47 tests covering:
- **Environment Reset** (7 tests): observation format, alarm generation, deterministic seeds
- **Topology** (8 tests): node counts, parent-child consistency, layer coverage, region coverage
- **Step Actions** (12 tests): all 5 action types, error handling, termination conditions
- **Graders** (9 tests): score ranges, F1 metrics, FP penalties, determinism
- **State Tracking** (4 tests): step counting, node tracking
- **Models** (4 tests): config validation, action schemas
- **Integration** (3 tests): full episode simulations for easy/medium/hard

---

## 🏆 Hackathon Rubric Mapping

For judges evaluating this submission, here is exactly where to find the evidence for each rubric criterion:

| Criterion | Evidence & Location |
|-----------|---------------------|
| **1. Functionality & Conformity** (Does it work? Does it match OpenEnv spec?) | ✅ Passes `openenv validate` (`artifacts/openenv_validate.txt`) <br> ✅ 6/6 exact OpenEnv API endpoints implemented in `app/main.py`. <br> ✅ State and Grading (F1/MTTR) cleanly decoupled. |
| **2. Code Quality & Testing** (Is it tested and documented?) | ✅ **47/47 PyTest coverage** running in 0.2s (`artifacts/pytest.txt`). <br> ✅ Extensive docstrings, type hinting (Pydantic v2 in `app/models.py`). <br> ✅ Clear architectural separation (server, engine, graders). |
| **3. Reproducibility** (Can baseline runs be reproduced?) | ✅ Strict seeding in `app/environment.py`. <br> ✅ Two identical automated runs produced the exact same trajectories/actions for all 3 tasks (`artifacts/reproducibility_test.txt`). |
| **4. Cloud & Docker Deployment** (Is it accessible?) | ✅ Fully containerised with `Dockerfile` and `server/app.py`. <br> ✅ Local Docker E2E smoke tests passed (`artifacts/docker_smoke.txt`). <br> ✅ **Live on Hugging Face Spaces:** [https://huggingface.co/spaces/ayushman098/telco-rca](https://huggingface.co/spaces/ayushman098/telco-rca). |
| **5. Innovation & Complexity** (Is the environment non-trivial?) | ✅ Massive 500-node graph scaling out across 5 regions. <br> ✅ Adversarial noise (40% spurious alarms testing robustness). <br> ✅ Novel *MTTR vs FP penalty* trade-off formulation. |

---

*Built with FastAPI · Pydantic v2 · OpenAI client · OpenEnv spec*
