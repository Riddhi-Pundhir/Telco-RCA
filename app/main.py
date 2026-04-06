"""
Telco-RCA FastAPI server — implements the OpenEnv HTTP interface.

Endpoints:
    POST /reset    — Start a new episode for a given task
    POST /step     — Execute an agent action
    GET  /state    — Internal state for debugging/grading
    GET  /tasks    — List all available tasks
    GET  /health   — Liveness check
    POST /grade    — Score a complete trajectory
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os

from .environment import TelcoRCAEnvironment
from .models import AgentAction, TASK_CONFIGS
from .graders import grade_easy, grade_medium, grade_hard, grade_episode

app = FastAPI(
    title="Telco-RCA OpenEnv",
    description=(
        "5G Network Root Cause Analysis — RL environment for fault diagnosis agents. "
        "Simulate cascading equipment failures across a layered telecom knowledge graph "
        "and train agents to identify the true root cause with minimum false positives."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route for the main UI
@app.get("/")
def serve_ui():
    static_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_path):
        return FileResponse(static_path)
    return {"error": "UI not built yet."}

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# One environment instance per task (stateful server)
_envs: dict[str, TelcoRCAEnvironment] = {}


def _get_env(task: str) -> TelcoRCAEnvironment:
    if task not in _envs:
        _envs[task] = TelcoRCAEnvironment(task_name=task)
    return _envs[task]


# ------------------------------------------------------------------ #
#  Request/response schemas                                            #
# ------------------------------------------------------------------ #

class ResetRequest(BaseModel):
    task: str = "easy"
    seed: int | None = None

class StepRequest(BaseModel):
    task: str = "easy"
    action: AgentAction

class GradeRequest(BaseModel):
    task: str
    trajectory: dict


# ------------------------------------------------------------------ #
#  Endpoints                                                           #
# ------------------------------------------------------------------ #

@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": "telco-rca",
        "version": "1.0.0",
        "tasks_available": list(TASK_CONFIGS.keys()),
    }


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "name": cfg.name,
                "description": cfg.description,
                "num_nodes": cfg.num_nodes,
                "max_steps": cfg.max_steps,
                "failure_layers": cfg.failure_layers,
                "noise_ratio": cfg.noise_ratio,
                "num_regions": cfg.num_regions,
            }
            for cfg in TASK_CONFIGS.values()
        ]
    }


@app.post("/reset")
def reset(req: ResetRequest):
    if req.task not in TASK_CONFIGS:
        raise HTTPException(400, f"Unknown task '{req.task}'. Valid: {list(TASK_CONFIGS)}")
    env = _get_env(req.task)
    obs = env.reset(seed=req.seed)
    return obs.model_dump()


@app.post("/step")
def step(req: StepRequest):
    if req.task not in TASK_CONFIGS:
        raise HTTPException(400, f"Unknown task '{req.task}'.")
    env = _get_env(req.task)
    try:
        result = env.step(req.action)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return result.model_dump()


@app.get("/state")
def state(task: str = "easy"):
    if task not in TASK_CONFIGS:
        raise HTTPException(400, f"Unknown task '{task}'.")
    return _get_env(task).state()


@app.post("/grade")
def grade(req: GradeRequest):
    if req.task not in TASK_CONFIGS:
        raise HTTPException(400, f"Unknown task '{req.task}'.")

    # Use the detailed grader with intelligence signals
    result = grade_episode(
        task_name=req.task,
        root_cause_fixed=req.trajectory.get("root_cause_fixed", False),
        steps_taken=req.trajectory.get("steps_taken", TASK_CONFIGS[req.task].max_steps),
        false_positives=req.trajectory.get("false_positives", 0),
        elapsed_seconds=req.trajectory.get("elapsed_seconds", 300),
        correct_diagnosis=req.trajectory.get("correct_diagnosis", False),
        checked_nodes=req.trajectory.get("checked_nodes"),
        checked_layers=req.trajectory.get("checked_layers"),
        total_nodes=req.trajectory.get("total_nodes", 0),
        total_layers_alarming=req.trajectory.get("total_layers_alarming", 0),
        action_log=req.trajectory.get("action_log"),
    )
    return {
        "task": req.task,
        "score": result["score"],
        "reason": result["reason"],
        "breakdown": result["breakdown"],
    }


def start():
    """Entry point for `openenv serve` / pyproject.toml scripts."""
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=7860)
