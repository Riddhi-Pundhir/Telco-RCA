# 🔴 Telco-RCA — 5G Network Root Cause Analysis Environment

> **OpenEnv submission** · Team Codyy AR · April 2026 Hackathon

An RL environment where an AI agent must diagnose cascading equipment failures in a 5G network — finding the one broken node responsible for hundreds of downstream alarms, as fast as possible, with minimum false positives.

---

## 🌐 The Problem

Modern 5G networks are massive graphs. When a **Power Unit** fails, it triggers a **cascade** — hundreds of downstream towers, radio controllers, and switches all emit alarms simultaneously. Human engineers take **hours** to find the real culprit. This environment trains agents to do it in **seconds**.

```
Power Unit  ──►  Core Switch  ──►  Radio Controller  ──►  Cell Tower
   [FAILED]         [ALARM]              [ALARM]              [ALARM]
                                         [ALARM]              [ALARM]
                                                              [ALARM]
```

---

## 🗂️ Project Structure

```
telco-rca/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI server (OpenEnv HTTP interface)
│   ├── environment.py   # Core simulation logic
│   ├── models.py        # Pydantic models for all I/O
│   └── graders.py       # Deterministic scoring functions
├── tests/
│   └── test_environment.py   # 15 unit tests
├── inference.py         # Mandatory baseline script
├── openenv.yaml         # OpenEnv spec
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 🎮 Tasks

| Task | Nodes | Alarms | Noise | Max Steps | Failure Layer |
|------|-------|--------|-------|-----------|---------------|
| **easy** | 20 | 5–10 | 0% | 15 | Power Unit only |
| **medium** | 100 | 20–50 | 20% | 30 | Power Unit, Core Switch |
| **hard** | 500 | 50–300 | 40% | 50 | All layers |

---

## ⚡ Actions

| Action | Cost | Effect |
|--------|------|--------|
| `CHECK_LOGS` | -0.01 | Read node error logs (textual clues) |
| `CHECK_VOLTAGE` | -0.01 | Measure voltage (low = hardware fault) |
| `RESTART` | -0.01 | Fix the network **if root cause** (+reward), else **false positive** (-0.3) |
| `DIAGNOSE` | -0.01 | Declare root cause without restarting (safer, lower max reward) |

---

## 📊 Reward / Grading

```
score = clamp(efficiency_mult + speed_bonus × 0.2 − fp_penalty, 0, 1)

  efficiency_mult = 1 − (steps_taken / max_steps)
  speed_bonus     = max(0, 1 − elapsed_seconds / 300)
  fp_penalty      = false_positives × 0.15
```

Scores are always in **[0.0, 1.0]** and are **deterministic** for a given trajectory.

---

## 🚀 Quick Start

### Local

```bash
pip install -r requirements.txt

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 7860

# Run tests
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
| `GET` | `/health` | Liveness check |
| `GET` | `/tasks` | List all tasks with metadata |
| `POST` | `/reset` | Start new episode `{"task": "easy"}` |
| `POST` | `/step` | Execute action `{"task": "easy", "action": {...}}` |
| `GET` | `/state` | Internal state (for debugging/grading) |
| `POST` | `/grade` | Score a trajectory `{"task": "easy", "trajectory": {...}}` |

### Example interaction

```bash
# Reset
curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" \
     -d '{"task": "easy"}'

# Step
curl -X POST http://localhost:7860/step -H "Content-Type: application/json" \
     -d '{"task": "easy", "action": {"action_type": "CHECK_VOLTAGE", "target_node_id": "PWR_000"}}'

# Grade
curl -X POST http://localhost:7860/grade -H "Content-Type: application/json" \
     -d '{"task": "easy", "trajectory": {"root_cause_fixed": true, "steps_taken": 4, "false_positives": 0, "elapsed_seconds": 12}}'
```

---

## 🧠 Agent Strategy (Baseline)

The LLM baseline uses a **top-down diagnosis** strategy:

1. Group active alarms by network layer
2. If all towers in a region alarm → suspect their shared Radio Controller
3. `CHECK_VOLTAGE` the suspect's parent (switch → power unit)
4. Walk up the tree until low voltage is found
5. `DIAGNOSE` or `RESTART` with high confidence

---

## 🏆 Why This Environment Matters

- **Real-world gap**: Telco operators spend millions/year on manual RCA. No public RL benchmark exists for this domain.
- **Graph reasoning**: Forces agents to understand parent-child causality, not just pattern-match alarms.
- **Adversarial noise**: 40% spurious alarms in hard mode test robustness.
- **MTTR metric**: Speed matters — every minute of downtime has a real cost.

---

## ⚙️ Required Environment Variables

```
API_BASE_URL   The LLM API endpoint
MODEL_NAME     Model identifier for inference
HF_TOKEN       Hugging Face / API key
```

---

*Built with FastAPI · Pydantic v2 · OpenAI client · OpenEnv spec*
