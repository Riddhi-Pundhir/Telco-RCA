"""
Telco-RCA Environment: Root Cause Analysis for 5G Network Failures
Simulates cascading alarm storms in a telecom network topology.
Agent must identify the true root cause node among hundreds of symptom alarms.
"""

import random
import time
from typing import Any
from collections import deque

from .models import (
    NetworkNode, Alarm, AgentObservation, AgentAction,
    StepResult, EpisodeState, TaskConfig, TASK_CONFIGS
)


class TelcoRCAEnvironment:
    """
    Simulates a 5G network where equipment failures propagate as alarm cascades.
    
    Topology: Power Units → Core Switches → Radio Controllers → Cell Towers
    When a parent fails, all downstream children generate symptom alarms.
    Agent must diagnose the root cause without sending unnecessary repair crews.
    """

    def __init__(self, task_name: str = "easy"):
        if task_name not in TASK_CONFIGS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(TASK_CONFIGS.keys())}")
        self.task_config: TaskConfig = TASK_CONFIGS[task_name]
        self.task_name = task_name
        self._state: EpisodeState | None = None
        self._start_time: float = 0.0

    # ------------------------------------------------------------------ #
    #  Public OpenEnv interface                                            #
    # ------------------------------------------------------------------ #

    def reset(self) -> AgentObservation:
        """Initialise a fresh episode with a new random failure injected."""
        cfg = self.task_config
        nodes = self._build_topology(cfg.num_nodes)
        root_cause_id = self._inject_failure(nodes, cfg)

        self._state = EpisodeState(
            nodes=nodes,
            root_cause_id=root_cause_id,
            active_alarms=self._propagate_alarms(nodes, root_cause_id, cfg),
            checked_nodes=set(),
            restarted_nodes=set(),
            steps_taken=0,
            max_steps=cfg.max_steps,
            false_positives=0,
            episode_done=False,
            start_time=time.time(),
        )
        self._start_time = time.time()
        return self._build_observation()

    def step(self, action: AgentAction) -> StepResult:
        """Execute one agent action and return (observation, reward, done, info)."""
        if self._state is None:
            raise RuntimeError("Call reset() before step()")
        if self._state.episode_done:
            raise RuntimeError("Episode is done. Call reset() to start a new one.")

        s = self._state
        s.steps_taken += 1
        reward = -0.01  # small step penalty encourages efficiency
        info: dict[str, Any] = {}

        if action.action_type == "CHECK_LOGS":
            reward, info = self._handle_check(action.target_node_id)
        elif action.action_type == "CHECK_VOLTAGE":
            reward, info = self._handle_voltage(action.target_node_id)
        elif action.action_type == "RESTART":
            reward, info = self._handle_restart(action.target_node_id)
        elif action.action_type == "DIAGNOSE":
            reward, info = self._handle_diagnose(action.target_node_id)
        else:
            reward = -0.1
            info["error"] = f"Unknown action: {action.action_type}"

        # Check termination conditions
        if s.steps_taken >= s.max_steps and not s.episode_done:
            s.episode_done = True
            info["termination"] = "max_steps_exceeded"

        obs = self._build_observation()
        return StepResult(
            observation=obs,
            reward=round(reward, 4),
            done=s.episode_done,
            info=info,
        )

    def get_state(self) -> dict:
        """Return full internal state for debugging / grader access."""
        if self._state is None:
            return {"status": "not_started"}
        s = self._state
        return {
            "root_cause_id": s.root_cause_id,
            "steps_taken": s.steps_taken,
            "false_positives": s.false_positives,
            "episode_done": s.episode_done,
            "checked_nodes": list(s.checked_nodes),
            "restarted_nodes": list(s.restarted_nodes),
            "active_alarm_count": len(s.active_alarms),
            "elapsed_seconds": round(time.time() - s.start_time, 2),
        }

    # ------------------------------------------------------------------ #
    #  Topology & failure simulation                                       #
    # ------------------------------------------------------------------ #

    def _build_topology(self, num_nodes: int) -> dict[str, NetworkNode]:
        """Build a layered 5G network topology."""
        nodes: dict[str, NetworkNode] = {}

        # Layer 0: Power Units (roots) — 1 per 20 nodes
        n_power = max(1, num_nodes // 20)
        for i in range(n_power):
            nid = f"PWR_{i:03d}"
            nodes[nid] = NetworkNode(
                node_id=nid, layer="power_unit",
                children=[], status="UP", alarm_text=None
            )

        # Layer 1: Core Switches — 1 per power unit, 2–4 switches each
        for p_idx in range(n_power):
            parent_id = f"PWR_{p_idx:03d}"
            n_sw = random.randint(2, 4)
            for s_idx in range(n_sw):
                nid = f"SW_{p_idx:02d}_{s_idx:02d}"
                nodes[nid] = NetworkNode(
                    node_id=nid, layer="core_switch",
                    children=[], status="UP", alarm_text=None
                )
                nodes[parent_id].children.append(nid)

        # Layer 2: Radio Controllers — 2–5 per switch
        switches = [n for n in nodes if n.startswith("SW_")]
        for sw_id in switches:
            n_rc = random.randint(2, 5)
            for rc_idx in range(n_rc):
                nid = f"RC_{sw_id[3:]}_{rc_idx:02d}"
                nodes[nid] = NetworkNode(
                    node_id=nid, layer="radio_controller",
                    children=[], status="UP", alarm_text=None
                )
                nodes[sw_id].children.append(nid)

        # Layer 3: Cell Towers — fill remaining quota
        rcs = [n for n in nodes if n.startswith("RC_")]
        towers_needed = max(0, num_nodes - len(nodes))
        per_rc = max(1, towers_needed // max(1, len(rcs)))
        for rc_id in rcs:
            for t_idx in range(per_rc):
                nid = f"TOWER_{rc_id[3:]}_{t_idx:02d}"
                nodes[nid] = NetworkNode(
                    node_id=nid, layer="cell_tower",
                    children=[], status="UP", alarm_text=None
                )
                nodes[rc_id].children.append(nid)

        return nodes

    def _inject_failure(self, nodes: dict[str, NetworkNode], cfg: TaskConfig) -> str:
        """Pick a root cause node and mark it as FAILED."""
        candidates = [
            nid for nid, n in nodes.items()
            if n.layer in cfg.failure_layers
        ]
        root_cause_id = random.choice(candidates)
        nodes[root_cause_id].status = "FAILED"
        nodes[root_cause_id].alarm_text = (
            f"CRITICAL: {nodes[root_cause_id].layer.upper()} hardware fault detected. "
            f"Voltage drop 34%. Kernel panic at 03:17 UTC."
        )
        return root_cause_id

    def _propagate_alarms(
        self, nodes: dict[str, NetworkNode], root_id: str, cfg: TaskConfig
    ) -> list[Alarm]:
        """BFS from root cause — downstream nodes emit symptom alarms."""
        alarms: list[Alarm] = []
        queue = deque(nodes[root_id].children)
        visited = {root_id}
        severity_cycle = ["WARNING", "MAJOR", "CRITICAL", "MINOR"]

        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            node = nodes[nid]
            node.status = "DEGRADED"
            sev = random.choice(severity_cycle)
            alarm_text = self._generate_alarm_text(node.layer, sev)
            node.alarm_text = alarm_text
            alarms.append(Alarm(
                node_id=nid, severity=sev,
                message=alarm_text, layer=node.layer
            ))
            # Add noise alarms (cfg-controlled)
            if random.random() < cfg.noise_ratio:
                alarms.append(Alarm(
                    node_id=nid, severity="WARNING",
                    message="Periodic heartbeat miss (transient)", layer=node.layer
                ))
            queue.extend(nodes[nid].children)

        random.shuffle(alarms)
        return alarms

    def _generate_alarm_text(self, layer: str, severity: str) -> str:
        templates = {
            "cell_tower": [
                f"{severity}: RF signal loss on sector A. RSRP below -110 dBm.",
                f"{severity}: Cell tower handover failure rate 78%. KPI breach.",
                f"{severity}: Backhaul link packet loss 23%. SLA violation.",
            ],
            "radio_controller": [
                f"{severity}: RRC connection setup failures spiked to 340/hr.",
                f"{severity}: Baseband unit temperature 91°C. Thermal threshold exceeded.",
                f"{severity}: Timing sync lost. GPS reference unavailable.",
            ],
            "core_switch": [
                f"{severity}: BGP session flap. Route withdrawal for 192.168.x.0/24.",
                f"{severity}: Port Gi0/1 CRC errors: 14,582 in last 5 min.",
                f"{severity}: OSPF adjacency dropped with peer 10.0.0.x.",
            ],
            "power_unit": [
                f"{severity}: UPS battery at 12%. Runtime estimate 8 minutes.",
                f"{severity}: Rectifier module 2 offline. Load redistributed.",
                f"{severity}: AC input phase C missing. Generator transfer pending.",
            ],
        }
        return random.choice(templates.get(layer, [f"{severity}: Unknown fault on {layer}."]))

    # ------------------------------------------------------------------ #
    #  Action handlers                                                     #
    # ------------------------------------------------------------------ #

    def _handle_check(self, node_id: str) -> tuple[float, dict]:
        s = self._state
        if node_id not in s.nodes:
            return -0.05, {"error": f"Node {node_id} not found"}
        s.checked_nodes.add(node_id)
        node = s.nodes[node_id]
        return 0.02, {
            "node_id": node_id, "status": node.status,
            "layer": node.layer, "log": node.alarm_text or "No anomalies in logs.",
        }

    def _handle_voltage(self, node_id: str) -> tuple[float, dict]:
        s = self._state
        if node_id not in s.nodes:
            return -0.05, {"error": f"Node {node_id} not found"}
        node = s.nodes[node_id]
        voltage = 48.0 if node.status == "UP" else round(random.uniform(18.0, 35.0), 1)
        s.checked_nodes.add(node_id)
        return 0.03, {
            "node_id": node_id, "voltage_v": voltage,
            "status": "NOMINAL" if voltage > 44 else "CRITICAL",
        }

    def _handle_restart(self, node_id: str) -> tuple[float, dict]:
        s = self._state
        if node_id not in s.nodes:
            return -0.05, {"error": f"Node {node_id} not found"}

        node = s.nodes[node_id]
        s.restarted_nodes.add(node_id)

        if node_id == s.root_cause_id:
            # Correct fix — clear all downstream alarms
            self._clear_downstream(node_id)
            elapsed = round(time.time() - s.start_time, 2)
            mttr_bonus = max(0.0, 1.0 - elapsed / 300)  # bonus for speed
            fp_penalty = s.false_positives * 0.15
            reward = 1.0 + mttr_bonus - fp_penalty
            s.episode_done = True
            return reward, {
                "result": "ROOT_CAUSE_FIXED",
                "mttr_seconds": elapsed,
                "false_positives": s.false_positives,
                "final_reward": round(reward, 4),
            }
        else:
            # Wrong node restarted — false positive
            s.false_positives += 1
            return -0.3, {
                "result": "FALSE_POSITIVE",
                "restarted": node_id,
                "note": "Node restarted but alarms persist. Network still degraded.",
            }

    def _handle_diagnose(self, node_id: str) -> tuple[float, dict]:
        """Agent submits its final root-cause diagnosis without restarting."""
        s = self._state
        if node_id == s.root_cause_id:
            elapsed = round(time.time() - s.start_time, 2)
            reward = 0.8 - s.false_positives * 0.1
            s.episode_done = True
            return reward, {
                "result": "CORRECT_DIAGNOSIS",
                "mttr_seconds": elapsed,
                "note": "Correct root cause identified.",
            }
        else:
            s.false_positives += 1
            return -0.2, {"result": "WRONG_DIAGNOSIS", "guessed": node_id}

    def _clear_downstream(self, node_id: str):
        s = self._state
        queue = deque([node_id])
        while queue:
            nid = queue.popleft()
            s.nodes[nid].status = "UP"
            s.nodes[nid].alarm_text = None
            queue.extend(s.nodes[nid].children)
        s.active_alarms = []

    def _build_observation(self) -> AgentObservation:
        s = self._state
        return AgentObservation(
            active_alarms=s.active_alarms[:50],  # cap to avoid token explosion
            total_alarm_count=len(s.active_alarms),
            steps_remaining=s.max_steps - s.steps_taken,
            false_positives_so_far=s.false_positives,
            checked_nodes=list(s.checked_nodes),
            episode_done=s.episode_done,
            task_description=self.task_config.description,
        )
