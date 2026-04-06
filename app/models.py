"""
Typed Pydantic models for the Telco-RCA OpenEnv environment.
All data crossing the API boundary is validated here.

Includes the network topology primitives, agent I/O schemas,
task configurations, and internal episode state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from pydantic import BaseModel, Field


Severity = Literal["MINOR", "WARNING", "MAJOR", "CRITICAL"]


# ------------------------------------------------------------------ #
#  Network topology primitives                                         #
# ------------------------------------------------------------------ #

class NetworkNode(BaseModel):
    """Represents a single piece of 5G network equipment."""
    node_id: str
    layer: Literal["power_unit", "core_switch", "radio_controller", "cell_tower"]
    children: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    status: Literal["UP", "DEGRADED", "FAILED"] = "UP"
    alarm_text: str | None = None
    region: str = "default"
    # Physical metadata for realistic diagnostics
    voltage: float = 48.0
    temperature_c: float = 35.0
    uptime_hours: float = 8760.0  # 1 year default


class Alarm(BaseModel):
    """An active alarm emitted by a network node."""
    alarm_id: str = ""
    node_id: str
    severity: Severity
    message: str
    layer: str
    timestamp: float = 0.0
    is_noise: bool = False  # hidden from agent, used by graders
    # Temporal metadata (simulation time, not wall clock)
    created_at_s: float = 0.0
    last_updated_at_s: float = 0.0
    age_s: float = 0.0
    # Propagation and escalation metadata
    depth_from_root: int = 0
    propagation_delay_s: float = 0.0
    escalation_count: int = 0
    last_escalated_at_s: float | None = None
    escalated_from: Severity | None = None
    source: Literal["root_cause", "cascade", "noise", "evolved_noise"] = "cascade"


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
    network_summary: dict = Field(default_factory=dict)
    simulation_time_s: float = 0.0
    alarm_age_summary: dict = Field(default_factory=dict)


class AgentAction(BaseModel):
    """
    action_type: one of CHECK_LOGS | CHECK_VOLTAGE | RESTART | DIAGNOSE | TRACE_PATH
    target_node_id: the node to act on
    """
    action_type: Literal["CHECK_LOGS", "CHECK_VOLTAGE", "RESTART", "DIAGNOSE", "TRACE_PATH"]
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
    num_regions: int = 1
    multi_root: bool = False  # future: allow >1 simultaneous root cause


TASK_CONFIGS: dict[str, TaskConfig] = {
    "easy": TaskConfig(
        name="easy",
        description=(
            "EASY: A single power unit has failed in a small 5G network of ~20 nodes. "
            "Roughly 5–10 downstream alarms with NO noise. Your job: classify the alarm "
            "(e.g. 'Mains Failure') and suggest a standard repair. "
            "Identify and fix the root cause within 15 steps."
        ),
        num_nodes=20,
        max_steps=15,
        failure_layers=["power_unit"],
        noise_ratio=0.0,
        num_regions=1,
    ),
    "medium": TaskConfig(
        name="medium",
        description=(
            "MEDIUM: A core switch or power unit has failed in a 100-node 5G network. "
            "You will see ~10–50 simultaneous alarms with 20% noise (spurious alerts). "
            "Correlate alarms across a cluster to find the ONE true faulty node. "
            "Diagnose root cause within 30 steps while minimising false positives."
        ),
        num_nodes=100,
        max_steps=30,
        failure_layers=["power_unit", "core_switch"],
        noise_ratio=0.2,
        num_regions=3,
    ),
    "hard": TaskConfig(
        name="hard",
        description=(
            "HARD: A cascading failure in a 500-node 5G Knowledge Graph. Any layer can fail. "
            "40% noise alarms. Up to 300 alarm events. Navigate physical and logical "
            "dependencies across multiple regions to stop a systemic outage. "
            "Solve within 50 steps. Heavy penalties for false positives — "
            "every wrong restart sends a real crew to the wrong location."
        ),
        num_nodes=500,
        max_steps=50,
        failure_layers=["power_unit", "core_switch", "radio_controller"],
        noise_ratio=0.4,
        num_regions=5,
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
    checked_nodes: set[str] = field(default_factory=set)
    restarted_nodes: set[str] = field(default_factory=set)
    diagnosed_nodes: set[str] = field(default_factory=set)
    steps_taken: int = 0
    max_steps: int = 15
    false_positives: int = 0
    episode_done: bool = False
    start_time: float = 0.0
    simulation_time_s: float = 0.0
    last_step_advanced_s: float = 0.0
    alarm_seq: int = 0
    topology_edges: list[tuple[str, str]] = field(default_factory=list)
    regions: dict[str, list[str]] = field(default_factory=dict)
    # Action history for grading intelligence signals
    action_log: list[dict] = field(default_factory=list)
