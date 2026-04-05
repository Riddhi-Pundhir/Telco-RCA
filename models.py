"""
Typed Pydantic models for the Telco-RCA OpenEnv environment.
All data crossing the API boundary is validated here.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
#  Network topology primitives                                         #
# ------------------------------------------------------------------ #

class NetworkNode(BaseModel):
    node_id: str
    layer: Literal["power_unit", "core_switch", "radio_controller", "cell_tower"]
    children: list[str] = Field(default_factory=list)
    status: Literal["UP", "DEGRADED", "FAILED"] = "UP"
    alarm_text: str | None = None


class Alarm(BaseModel):
    node_id: str
    severity: Literal["MINOR", "WARNING", "MAJOR", "CRITICAL"]
    message: str
    layer: str


# ------------------------------------------------------------------ #
#  Agent-facing I/O                                                    #
# ------------------------------------------------------------------ #

class AgentObservation(BaseModel):
    """What the agent sees at each step."""
    active_alarms: list[Alarm]
    total_alarm_count: int
    steps_remaining: int
    false_positives_so_far: int
    checked_nodes: list[str]
    episode_done: bool
    task_description: str


class AgentAction(BaseModel):
    """
    action_type: one of CHECK_LOGS | CHECK_VOLTAGE | RESTART | DIAGNOSE
    target_node_id: the node to act on
    """
    action_type: Literal["CHECK_LOGS", "CHECK_VOLTAGE", "RESTART", "DIAGNOSE"]
    target_node_id: str


class StepResult(BaseModel):
    observation: AgentObservation
    reward: float
    done: bool
    info: dict


# ------------------------------------------------------------------ #
#  Task configuration                                                  #
# ------------------------------------------------------------------ #

class TaskConfig(BaseModel):
    name: str
    description: str
    num_nodes: int
    max_steps: int
    failure_layers: list[str]
    noise_ratio: float  # probability of extra noise alarms per node


TASK_CONFIGS: dict[str, TaskConfig] = {
    "easy": TaskConfig(
        name="easy",
        description=(
            "EASY: A single power unit has failed in a small network of ~20 nodes. "
            "Roughly 5–10 downstream alarms. Identify and fix the root cause within 15 steps."
        ),
        num_nodes=20,
        max_steps=15,
        failure_layers=["power_unit"],
        noise_ratio=0.0,
    ),
    "medium": TaskConfig(
        name="medium",
        description=(
            "MEDIUM: A core switch or radio controller has failed in a 100-node network. "
            "Up to 50 alarms with 20% noise. Diagnose root cause within 30 steps "
            "while minimising false positives."
        ),
        num_nodes=100,
        max_steps=30,
        failure_layers=["power_unit", "core_switch"],
        noise_ratio=0.2,
    ),
    "hard": TaskConfig(
        name="hard",
        description=(
            "HARD: A cascading failure in a 500-node 5G network. Any layer can fail. "
            "40% noise alarms. Up to 300 alarm events. Solve within 50 steps. "
            "Heavy penalties for false positives — every wrong restart costs the operator."
        ),
        num_nodes=500,
        max_steps=50,
        failure_layers=["power_unit", "core_switch", "radio_controller"],
        noise_ratio=0.4,
    ),
}


# ------------------------------------------------------------------ #
#  Internal episode state (not exposed over API)                       #
# ------------------------------------------------------------------ #

@dataclass
class EpisodeState:
    nodes: dict[str, NetworkNode]
    root_cause_id: str
    active_alarms: list[Alarm]
    checked_nodes: set[str]
    restarted_nodes: set[str]
    steps_taken: int
    max_steps: int
    false_positives: int
    episode_done: bool
    start_time: float
