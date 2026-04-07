---
title: Telco-RCA
emoji: 📡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

<p align="center">
  <img src="https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/radio-tower.svg" width="88" alt="Telco-RCA logo">
</p>

<h1 align="center">Telco-RCA</h1>
<p align="center">
  <strong>OpenEnv telecom root-cause analysis, built for graph reasoning agents</strong>
</p>

<p align="center">
  <a href="https://ayushman098-telco-rca.hf.space/">
    <img src="https://img.shields.io/badge/Live%20Dashboard-Hugging%20Face-blue?style=for-the-badge&logo=huggingface" alt="Live Dashboard">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11+-black?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/OpenEnv-validated-success?style=for-the-badge" alt="OpenEnv">
</p>

> Telco-RCA turns a telecom outage into a reasoning problem. Each episode drops an agent into a layered 5G network where one hidden failure fans out into alarms, misleading signals, and cascading symptoms. The agent must inspect the graph, narrow the blast radius, and repair the right node with as few mistakes as possible.

## Why this environment exists

Real telecom operations are not clean puzzle boards. They are noisy, layered, and time sensitive.
When a power unit fails, the alarms do not stay local. They ripple through switches, radio controllers, and towers across multiple regions.
Telco-RCA models that workflow in a way that is useful for:

- diagnosing root causes in a dependency graph
- practicing decision-making under alarm noise
- comparing agents on efficiency, accuracy, and recovery speed
- visualizing how an agent actually reasoned through the incident

## At a glance

- Four difficulty tiers: `easy`, `medium`, `hard`, and `extreme`
- Deterministic OpenEnv episodes with typed models and repeatable seeds
- Action-based diagnosis with logs, voltage checks, tracing, restart, and final diagnosis
- Reward shaping that balances efficiency, correctness, and false positives
- Trajectory replay with path history, reward breakdown, and heatmap data
- Dockerized deployment for local use and Hugging Face Spaces

## What makes it a strong benchmark

- Real-world utility: it models a telecom network operations workflow, not a toy game
- Task quality: the tier ladder is clean, reproducible, and gets harder in meaningful ways
- Environment design: the observation and action spaces stay typed, bounded, and interpretable
- Feedback quality: step rewards, terminal scores, and trajectory logs all tell part of the story
- Deployment readiness: it runs locally, in Docker, and on Hugging Face Spaces with the same API surface

## Episode flow

An episode usually feels like this:

1. The agent sees a storm of alarms and a compressed graph of the incident.
2. It starts with cheap, informative actions such as `CHECK_LOGS` or `CHECK_VOLTAGE`.
3. If the path looks suspicious, it traces upstream dependencies to find where the cascade began.
4. It commits to a restart or diagnosis only after the graph evidence is strong enough.
5. The trajectory panel shows the route taken, the reward earned, and the nodes that were inspected along the way.

## Incident story

<p align="center">
  <img src="assets/readme-cascade.png" alt="Telco-RCA incident cascade figure" width="100%">
</p>

The environment simulates a layered network where a single root fault can trigger a long alarm chain. Higher tiers add:

- larger topologies
- deeper dependency trees
- more noise and false alarms
- stricter pressure on recovery time

## Task tiers

| Task | Nodes | Regions | Max Steps | Noise | What it tests |
|:---|:---:|:---:|:---:|:---:|:---|
| `easy` | 20 | 1 | 15 | 0% | Basic fault isolation in a small network |
| `medium` | 100 | 3 | 30 | 20% | Correlating multiple alarms across a cluster |
| `hard` | 500 | 5 | 50 | 40% | Multi-hop reasoning across a large topology |
| `extreme` | 1000 | 8 | 75 | 60% | Worst-case RCA under heavy noise and deep cascades |

Each reset builds the exact configured node count for the chosen tier.

## Action space

| Action | What it does |
|:---|:---|
| `CHECK_LOGS` | Inspect node logs and alarm context |
| `CHECK_VOLTAGE` | Measure voltage for hardware diagnosis |
| `TRACE_PATH` | Walk the dependency chain from a node upward |
| `RESTART` | Repair the selected node if it is the true root cause |
| `DIAGNOSE` | Declare the likely root cause without restarting it |

## Observation space

Agents receive a structured observation with:

- active alarms and total alarm count
- steps remaining and episode completion state
- checked nodes and false positives so far
- network summary by layer and region
- simulation time and alarm age statistics
- a graph snapshot for graph-aware policies and visualization

## Reward and grading

The environment gives step-level shaping, while the final grade normalizes the run into a score between `0.0` and `1.0`.

Core signals:

- fewer steps is better
- faster recovery is better
- fewer false positives is better
- correct diagnosis and repair matter more than brute-force exploration

The grading layer also tracks:

- root-cause identification quality
- MTTR-style recovery speed
- false-positive penalties
- checked node and layer coverage

## Trajectory view

Telco-RCA includes a trajectory endpoint and dashboard panel that show how the agent solved the incident:

- agent path through the graph
- actions taken with timing
- reward breakdown per step
- heatmap of checked nodes
- replay scrubber for stepping through the episode

This is useful when you want to understand not just whether an agent succeeded, but how it reasoned.

## Quick start

### Docker

```bash
docker build -t telco-rca .
docker run -p 7860:7860 \
  -e API_BASE_URL=https://api.anthropic.com/v1 \
  -e MODEL_NAME=claude-sonnet-4-20250514 \
  -e HF_TOKEN=your_key \
  -e PUBLIC_BASE_URL=http://localhost:7860 \
  -e INTERNAL_API_TOKEN=change-me \
  telco-rca
```

Open `http://localhost:7860` after the container starts.

### Local development

```bash
pip install -r requirements.txt
npm ci

# Terminal 1
uvicorn app.main:app --host 0.0.0.0 --port 7860

# Terminal 2
npm run dev

# Production frontend build
npm run build
```

The built frontend is served from `app/static/` by FastAPI.

### Baseline agent

`inference.py` runs a reproducible baseline and accepts either `HF_TOKEN` or `OPENAI_API_KEY`.

```bash
SERVER_URL=https://ayushman098-telco-rca.hf.space python inference.py
```

### Benchmark sweep

`run_baseline.sh` runs multiple episodes per tier and writes a summary with mean score, standard deviation, and MTTR-style timing.

```bash
chmod +x run_baseline.sh
./run_baseline.sh --episodes 5 --output artifacts/baseline_report.txt
```

An example output format is stored in:

- `artifacts/baseline_report_example.txt`

## Hugging Face Space configuration

Set these secrets in the Space settings:

- `HF_TOKEN` or `OPENAI_API_KEY`
- `API_BASE_URL`
- `MODEL_NAME`
- `PUBLIC_BASE_URL`
- `INTERNAL_API_TOKEN` if you want to enable `/state/internal`
- `ALLOWED_ORIGINS` if you want to override the default CORS policy

The Space container now exposes a readiness route at `GET /ready`, and the Docker healthcheck uses that endpoint.

## API reference

| Method | Path | Purpose |
|:---|:---|:---|
| `GET` | `/health` | Liveness and version check |
| `GET` | `/ready` | Readiness check for the UI assets and task registry |
| `GET` | `/tasks` | List all available task tiers |
| `POST` | `/reset` | Start a new episode |
| `POST` | `/step` | Apply an agent action |
| `GET` | `/state` | Safe runtime state for the UI and agents |
| `GET` | `/trajectory` | Step-by-step replay, reward series, and node heatmap |
| `GET` | `/state/internal` | Token-protected debug state |
| `POST` | `/grade` | Score a full trajectory |

## Project structure

```text
.
├── app/                  # FastAPI backend, environment, models, graders
├── src/                  # React dashboard and visualization components
├── inference.py          # Baseline agent runner
├── run_baseline.sh       # Multi-episode benchmark sweep
├── openenv.yaml          # OpenEnv manifest
├── Dockerfile            # Space-ready container build
└── artifacts/            # Reproducibility and benchmark logs
```

## Validation

The repository includes:

- OpenEnv manifest metadata in `openenv.yaml`
- typed Pydantic models for observations, actions, and trajectories
- a Docker build that serves both API and frontend from one container
- a live dashboard on Hugging Face Spaces
- reproducibility logs and benchmark outputs under `artifacts/`

## License

MIT
