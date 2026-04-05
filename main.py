"""
Telco-RCA FastAPI server — implements the OpenEnv HTTP interface.
Endpoints: POST /reset, POST /step, GET /state, GET /tasks, GET /health
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .environment import TelcoRCAEnvironment
from .models import AgentAction, TASK_CONFIGS
from .graders import grade_easy, grade_medium, grade_hard

app = FastAPI(
    title="Telco-RCA OpenEnv",
    description="5G Network Root Cause Analysis — RL environment for fault diagnosis agents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# One environment instance per session (stateful server)
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
    return {"status": "ok", "environment": "telco-rca", "version": "1.0.0"}


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "name": cfg.name,
                "description": cfg.description,
                "num_nodes": cfg.num_nodes,
                "max_steps": cfg.max_steps,
            }
            for cfg in TASK_CONFIGS.values()
        ]
    }


@app.post("/reset")
def reset(req: ResetRequest):
    if req.task not in TASK_CONFIGS:
        raise HTTPException(400, f"Unknown task '{req.task}'. Valid: {list(TASK_CONFIGS)}")
    env = _get_env(req.task)
    obs = env.reset()
    return obs.model_dump()


@app.post("/step")
def step(req: StepRequest):
    if req.task not in TASK_CONFIGS:
        raise HTTPException(400, f"Unknown task '{req.task}'.")
    env = _get_env(req.task)
    result = env.step(req.action)
    return result.model_dump()


@app.get("/state")
def state(task: str = "easy"):
    if task not in TASK_CONFIGS:
        raise HTTPException(400, f"Unknown task '{task}'.")
    return _get_env(task).get_state()


@app.post("/grade")
def grade(req: GradeRequest):
    graders = {"easy": grade_easy, "medium": grade_medium, "hard": grade_hard}
    if req.task not in graders:
        raise HTTPException(400, f"Unknown task '{req.task}'.")
    score = graders[req.task](req.trajectory)
    return {"task": req.task, "score": score}
