"""
Telco-RCA Environment: Root Cause Analysis for 5G Network Failures
===================================================================

Simulates cascading alarm storms in a realistic telecom network topology.
The agent must identify the true root cause node among hundreds of symptom
alarms, navigating a layered knowledge graph of physical and logical
dependencies.

Topology:  Power Units → Core Switches → Radio Controllers → Cell Towers
Failure model: when a parent node fails, ALL downstream children emit
symptom alarms.  Noise alarms (transient/spurious) are injected at a
configurable ratio to confound diagnosis.

Key features:
  - Hierarchical 4-layer topology with realistic branching factors
  - Region-based clustering (nodes grouped by geographic region)
  - Parent tracking for upward traversal
  - Realistic alarm text templates with telco-specific terminology
  - Physical diagnostics (voltage, temperature, uptime)
  - TRACE_PATH action for inspecting parent–child relationships
  - Deterministic grading via F1 + MTTR scoring
"""

import random
import time
import uuid
from typing import Any
from collections import deque, Counter

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

    def reset(self, seed: int | None = None) -> AgentObservation:
        """Initialise a fresh episode with a new random failure injected."""
        if seed is not None:
            random.seed(seed)

        cfg = self.task_config
        nodes, edges, regions = self._build_topology(cfg.num_nodes, cfg.num_regions)
        root_cause_id = self._inject_failure(nodes, cfg)

        self._state = EpisodeState(
            nodes=nodes,
            root_cause_id=root_cause_id,
            active_alarms=self._propagate_alarms(nodes, root_cause_id, cfg),
            checked_nodes=set(),
            restarted_nodes=set(),
            diagnosed_nodes=set(),
            steps_taken=0,
            max_steps=cfg.max_steps,
            false_positives=0,
            episode_done=False,
            start_time=time.time(),
            topology_edges=edges,
            regions=regions,
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
        elif action.action_type == "TRACE_PATH":
            reward, info = self._handle_trace_path(action.target_node_id)
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
            "root_cause_layer": s.nodes[s.root_cause_id].layer,
            "steps_taken": s.steps_taken,
            "false_positives": s.false_positives,
            "episode_done": s.episode_done,
            "checked_nodes": list(s.checked_nodes),
            "restarted_nodes": list(s.restarted_nodes),
            "diagnosed_nodes": list(s.diagnosed_nodes),
            "active_alarm_count": len(s.active_alarms),
            "total_nodes": len(s.nodes),
            "elapsed_seconds": round(time.time() - s.start_time, 2),
            "topology_edge_count": len(s.topology_edges),
            "regions": {k: len(v) for k, v in s.regions.items()},
        }

    # ------------------------------------------------------------------ #
    #  Topology & failure simulation                                       #
    # ------------------------------------------------------------------ #

    def _build_topology(
        self, num_nodes: int, num_regions: int = 1
    ) -> tuple[dict[str, NetworkNode], list[tuple[str, str]], dict[str, list[str]]]:
        """
        Build a layered 5G network topology with region clustering.

        Layers:
          0 - Power Units   (roots) — ~1 per 20 nodes
          1 - Core Switches         — 2–4 per power unit
          2 - Radio Controllers     — 2–5 per switch
          3 - Cell Towers           — fill remaining quota

        Returns:
            (nodes_dict, edge_list, region_dict)
        """
        nodes: dict[str, NetworkNode] = {}
        edges: list[tuple[str, str]] = []
        regions: dict[str, list[str]] = {f"region_{i}": [] for i in range(num_regions)}
        region_names = list(regions.keys())

        # ── Layer 0: Power Units ──
        n_power = max(1, num_nodes // 20)
        for i in range(n_power):
            nid = f"PWR_{i:03d}"
            region = region_names[i % num_regions]
            nodes[nid] = NetworkNode(
                node_id=nid, layer="power_unit",
                children=[], parent_id=None, status="UP",
                alarm_text=None, region=region,
                voltage=48.0, temperature_c=round(random.uniform(28, 42), 1),
                uptime_hours=round(random.uniform(100, 20000), 1),
            )
            regions[region].append(nid)

        # ── Layer 1: Core Switches ──
        for p_idx in range(n_power):
            parent_id = f"PWR_{p_idx:03d}"
            n_sw = random.randint(2, 4)
            for s_idx in range(n_sw):
                nid = f"SW_{p_idx:02d}_{s_idx:02d}"
                region = nodes[parent_id].region
                nodes[nid] = NetworkNode(
                    node_id=nid, layer="core_switch",
                    children=[], parent_id=parent_id, status="UP",
                    alarm_text=None, region=region,
                    voltage=48.0, temperature_c=round(random.uniform(30, 55), 1),
                    uptime_hours=round(random.uniform(100, 15000), 1),
                )
                nodes[parent_id].children.append(nid)
                edges.append((parent_id, nid))
                regions[region].append(nid)

        # ── Layer 2: Radio Controllers ──
        switches = [n for n in nodes if n.startswith("SW_")]
        for sw_id in switches:
            n_rc = random.randint(2, 5)
            for rc_idx in range(n_rc):
                nid = f"RC_{sw_id[3:]}_{rc_idx:02d}"
                region = nodes[sw_id].region
                nodes[nid] = NetworkNode(
                    node_id=nid, layer="radio_controller",
                    children=[], parent_id=sw_id, status="UP",
                    alarm_text=None, region=region,
                    voltage=48.0, temperature_c=round(random.uniform(35, 65), 1),
                    uptime_hours=round(random.uniform(100, 12000), 1),
                )
                nodes[sw_id].children.append(nid)
                edges.append((sw_id, nid))
                regions[region].append(nid)

        # ── Layer 3: Cell Towers — fill remaining quota ──
        rcs = [n for n in nodes if n.startswith("RC_")]
        towers_needed = max(0, num_nodes - len(nodes))
        per_rc = max(1, towers_needed // max(1, len(rcs)))
        t_global = 0
        for rc_id in rcs:
            for t_idx in range(per_rc):
                nid = f"TOWER_{rc_id[3:]}_{t_idx:02d}"
                region = nodes[rc_id].region
                nodes[nid] = NetworkNode(
                    node_id=nid, layer="cell_tower",
                    children=[], parent_id=rc_id, status="UP",
                    alarm_text=None, region=region,
                    voltage=48.0, temperature_c=round(random.uniform(20, 50), 1),
                    uptime_hours=round(random.uniform(50, 10000), 1),
                )
                nodes[rc_id].children.append(nid)
                edges.append((rc_id, nid))
                regions[region].append(nid)
                t_global += 1
                if len(nodes) >= num_nodes:
                    break
            if len(nodes) >= num_nodes:
                break

        return nodes, edges, regions

    def _inject_failure(self, nodes: dict[str, NetworkNode], cfg: TaskConfig) -> str:
        """Pick a root cause node and mark it as FAILED with realistic diagnostics."""
        candidates = [
            nid for nid, n in nodes.items()
            if n.layer in cfg.failure_layers
        ]
        root_cause_id = random.choice(candidates)
        node = nodes[root_cause_id]
        node.status = "FAILED"
        node.voltage = round(random.uniform(8.0, 22.0), 1)
        node.temperature_c = round(random.uniform(75, 110), 1)

        # Generate a rich, layer-specific root cause alarm
        root_alarm_templates = {
            "power_unit": [
                f"CRITICAL: MAINS FAILURE — AC input lost on all phases. "
                f"UPS battery draining at {node.voltage}V. Estimated runtime: "
                f"{max(1, int(node.voltage / 4))} minutes. Rectifier offline. "
                f"Generator auto-transfer FAILED.",
                f"CRITICAL: DC power bus voltage collapsed to {node.voltage}V "
                f"(nominal 48V). Thermal runaway detected at {node.temperature_c}°C. "
                f"Battery bank disconnected. All downstream loads at risk.",
            ],
            "core_switch": [
                f"CRITICAL: Fabric switch ASIC failure on slot 3. "
                f"All line cards isolated. BGP/OSPF sessions torn down. "
                f"Voltage drooping to {node.voltage}V. CPU temperature {node.temperature_c}°C.",
                f"CRITICAL: Backplane communication lost. "
                f"CRC error storm: 142,000 errors/sec. Port channels flapping. "
                f"Voltage: {node.voltage}V.",
            ],
            "radio_controller": [
                f"CRITICAL: BBU hardware fault. CPRI links to all RRUs lost. "
                f"Baseband processing halted. Voltage: {node.voltage}V. "
                f"Temperature: {node.temperature_c}°C. No handover capacity.",
                f"CRITICAL: GPS timing reference lost AND internal oscillator failed. "
                f"All cells desynchronised. CPRI frame alignment errors. "
                f"Voltage: {node.voltage}V.",
            ],
        }
        templates = root_alarm_templates.get(node.layer, [
            f"CRITICAL: Hardware fault on {node.layer}. Voltage: {node.voltage}V"
        ])
        node.alarm_text = random.choice(templates)

        return root_cause_id

    def _propagate_alarms(
        self, nodes: dict[str, NetworkNode], root_id: str, cfg: TaskConfig
    ) -> list[Alarm]:
        """
        BFS from root cause — downstream nodes emit symptom alarms.
        Also adds noise alarms on non-affected nodes for harder tasks.
        """
        alarms: list[Alarm] = []
        queue = deque(nodes[root_id].children)
        visited = {root_id}
        severity_cycle = ["WARNING", "MAJOR", "CRITICAL", "MINOR"]
        alarm_counter = 0
        base_time = time.time()

        # Root cause's own alarm
        alarms.append(Alarm(
            alarm_id=f"ALM_{alarm_counter:05d}",
            node_id=root_id,
            severity="CRITICAL",
            message=nodes[root_id].alarm_text or "CRITICAL: Hardware fault",
            layer=nodes[root_id].layer,
            timestamp=base_time,
            is_noise=False,
        ))
        alarm_counter += 1

        # Propagate downstream
        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            node = nodes[nid]
            node.status = "DEGRADED"
            node.voltage = round(random.uniform(25.0, 40.0), 1)

            sev = random.choice(severity_cycle)
            alarm_text = self._generate_alarm_text(node.layer, sev)
            node.alarm_text = alarm_text

            alarms.append(Alarm(
                alarm_id=f"ALM_{alarm_counter:05d}",
                node_id=nid,
                severity=sev,
                message=alarm_text,
                layer=node.layer,
                timestamp=base_time + random.uniform(0.1, 5.0),
                is_noise=False,
            ))
            alarm_counter += 1

            # Noise alarm on this node (duplicate / transient)
            if random.random() < cfg.noise_ratio:
                alarms.append(Alarm(
                    alarm_id=f"ALM_{alarm_counter:05d}",
                    node_id=nid,
                    severity="WARNING",
                    message="Periodic heartbeat miss (transient)",
                    layer=node.layer,
                    timestamp=base_time + random.uniform(0.5, 10.0),
                    is_noise=True,
                ))
                alarm_counter += 1

            queue.extend(nodes[nid].children)

        # Extra noise: alarms from completely unrelated nodes
        if cfg.noise_ratio > 0:
            unaffected = [
                nid for nid in nodes
                if nid not in visited and nodes[nid].layer != "power_unit"
            ]
            noise_count = int(len(unaffected) * cfg.noise_ratio * 0.3)
            for nid in random.sample(unaffected, min(noise_count, len(unaffected))):
                sev = random.choice(["MINOR", "WARNING"])
                alarms.append(Alarm(
                    alarm_id=f"ALM_{alarm_counter:05d}",
                    node_id=nid,
                    severity=sev,
                    message=self._generate_noise_text(nodes[nid].layer),
                    layer=nodes[nid].layer,
                    timestamp=base_time + random.uniform(0, 15.0),
                    is_noise=True,
                ))
                alarm_counter += 1

        random.shuffle(alarms)
        return alarms

    def _generate_alarm_text(self, layer: str, severity: str) -> str:
        """Generate realistic alarm text for a given layer and severity."""
        templates = {
            "cell_tower": [
                f"{severity}: RF signal loss on sector A. RSRP below -110 dBm. UE disconnections: 342.",
                f"{severity}: Cell tower handover failure rate 78%. KPI breach on inter-frequency HO.",
                f"{severity}: Backhaul link packet loss 23%. SLA violation. Jitter 45ms.",
                f"{severity}: VSWR alarm on antenna port 1. Forward power dropped 6dB.",
                f"{severity}: RRU communication timeout. CPRI link layer2 sync lost.",
            ],
            "radio_controller": [
                f"{severity}: RRC connection setup failures spiked to 340/hr. Capacity impacted.",
                f"{severity}: Baseband unit temperature 91°C. Thermal threshold exceeded.",
                f"{severity}: Timing sync lost. GPS reference unavailable for 120s.",
                f"{severity}: S1 interface to EPC down. All UE context lost. MME unreachable.",
                f"{severity}: PDCP layer errors. Data radio bearer setup failures at 42%.",
            ],
            "core_switch": [
                f"{severity}: BGP session flap. Route withdrawal for 192.168.x.0/24. AS path unstable.",
                f"{severity}: Port Gi0/1 CRC errors: 14,582 in last 5 min. Possible cable/transceiver fault.",
                f"{severity}: OSPF adjacency dropped with peer 10.0.0.x. Area 0 reconverging.",
                f"{severity}: MPLS LSP tunnel down. Traffic shifted to backup path, 340ms RTT increase.",
                f"{severity}: ARP table overflow. MAC flapping on VLAN 100. Loop suspected.",
            ],
            "power_unit": [
                f"{severity}: UPS battery at 12%. Runtime estimate 8 minutes. Load shedding imminent.",
                f"{severity}: Rectifier module 2 offline. Load redistributed to modules 1,3.",
                f"{severity}: AC input phase C missing. Generator transfer pending. Fuel level: 34%.",
                f"{severity}: DC bus voltage fluctuating 44-51V. Ripple exceeds 2% threshold.",
            ],
        }
        return random.choice(templates.get(layer, [f"{severity}: Unknown fault on {layer}."]))

    def _generate_noise_text(self, layer: str) -> str:
        """Generate a plausible but spurious alarm (noise) for a healthy node."""
        noise_templates = {
            "cell_tower": [
                "MINOR: Scheduled RSSI measurement deviation +2dB. Within tolerance.",
                "WARNING: Antenna tilt adjusted by RAN optimiser. Performance nominal.",
                "MINOR: Temporary UE camping spike during event. Self-resolved.",
            ],
            "radio_controller": [
                "MINOR: License usage at 80%. Capacity planning advisory.",
                "WARNING: Software patch pending. Auto-install scheduled 03:00 UTC.",
                "MINOR: Inter-RAT handover success rate dipped to 96%. Monitoring.",
            ],
            "core_switch": [
                "MINOR: NTP clock drift 12ms. Resynchronising with stratum-1 source.",
                "WARNING: SNMP trap: ifOperStatus change on management interface. Auto-recovered.",
                "MINOR: ACL hit count anomaly on rule 47. Logging enabled.",
            ],
            "power_unit": [
                "MINOR: Battery equalisation charge cycle completed normally.",
                "WARNING: Environmental sensor: humidity at 72%. Within operating range.",
            ],
        }
        return random.choice(noise_templates.get(layer, ["MINOR: Transient event. Self-cleared."]))

    # ------------------------------------------------------------------ #
    #  Action handlers                                                     #
    # ------------------------------------------------------------------ #

    def _handle_check(self, node_id: str) -> tuple[float, dict]:
        """CHECK_LOGS: Read error logs for a node."""
        s = self._state
        if node_id not in s.nodes:
            return -0.05, {"error": f"Node {node_id} not found in topology"}
        s.checked_nodes.add(node_id)
        node = s.nodes[node_id]

        # Build a rich log response
        log_data = {
            "node_id": node_id,
            "status": node.status,
            "layer": node.layer,
            "region": node.region,
            "parent": node.parent_id,
            "children_count": len(node.children),
            "log": node.alarm_text or "No anomalies in logs. System operating normally.",
            "uptime_hours": node.uptime_hours,
        }

        # Extra hint if this is the root cause
        if node_id == s.root_cause_id:
            log_data["log"] += " [KERNEL PANIC] System halted. Manual intervention required."

        return 0.02, log_data

    def _handle_voltage(self, node_id: str) -> tuple[float, dict]:
        """CHECK_VOLTAGE: Measure voltage — smoking gun for hardware faults."""
        s = self._state
        if node_id not in s.nodes:
            return -0.05, {"error": f"Node {node_id} not found in topology"}

        node = s.nodes[node_id]
        s.checked_nodes.add(node_id)

        return 0.03, {
            "node_id": node_id,
            "voltage_v": node.voltage,
            "temperature_c": node.temperature_c,
            "status": "NOMINAL" if node.voltage > 44 else (
                "WARNING" if node.voltage > 30 else "CRITICAL"
            ),
            "layer": node.layer,
            "threshold": "48V nominal, <30V = hardware fault",
        }

    def _handle_trace_path(self, node_id: str) -> tuple[float, dict]:
        """TRACE_PATH: Show the full path from this node up to the root of the tree."""
        s = self._state
        if node_id not in s.nodes:
            return -0.05, {"error": f"Node {node_id} not found in topology"}
        s.checked_nodes.add(node_id)

        path = []
        current = node_id
        while current:
            node = s.nodes[current]
            path.append({
                "node_id": current,
                "layer": node.layer,
                "status": node.status,
                "region": node.region,
            })
            current = node.parent_id

        children_info = []
        for child_id in s.nodes[node_id].children:
            child = s.nodes[child_id]
            children_info.append({
                "node_id": child_id,
                "layer": child.layer,
                "status": child.status,
            })

        return 0.02, {
            "node_id": node_id,
            "path_to_root": path,
            "direct_children": children_info,
            "depth": len(path) - 1,
        }

    def _handle_restart(self, node_id: str) -> tuple[float, dict]:
        """RESTART: Fix the network IF this is the root cause. Heavy FP penalty if not."""
        s = self._state
        if node_id not in s.nodes:
            return -0.05, {"error": f"Node {node_id} not found in topology"}

        node = s.nodes[node_id]
        s.restarted_nodes.add(node_id)

        if node_id == s.root_cause_id:
            # ✅ Correct fix — clear all downstream alarms
            self._clear_downstream(node_id)
            elapsed = round(time.time() - s.start_time, 2)
            mttr_bonus = max(0.0, 1.0 - elapsed / 300)  # bonus for speed
            fp_penalty = s.false_positives * 0.15
            reward = 1.0 + mttr_bonus - fp_penalty
            s.episode_done = True
            return reward, {
                "result": "ROOT_CAUSE_FIXED",
                "root_cause_id": node_id,
                "root_cause_layer": node.layer,
                "mttr_seconds": elapsed,
                "false_positives": s.false_positives,
                "final_reward": round(reward, 4),
                "alarms_cleared": len(s.active_alarms),
            }
        else:
            # ❌ Wrong node restarted — false positive penalty
            s.false_positives += 1
            return -0.3, {
                "result": "FALSE_POSITIVE",
                "restarted": node_id,
                "restarted_layer": node.layer,
                "false_positives_total": s.false_positives,
                "note": (
                    "Node restarted but alarms persist. Network still degraded. "
                    "A field crew was dispatched to the wrong location."
                ),
            }

    def _handle_diagnose(self, node_id: str) -> tuple[float, dict]:
        """DIAGNOSE: Declare root cause without restarting (safer, less reward)."""
        s = self._state
        s.diagnosed_nodes.add(node_id)

        if node_id == s.root_cause_id:
            elapsed = round(time.time() - s.start_time, 2)
            mttr_bonus = max(0.0, 1.0 - elapsed / 300)
            fp_penalty = s.false_positives * 0.1
            reward = 0.8 + mttr_bonus * 0.5 - fp_penalty
            s.episode_done = True
            return reward, {
                "result": "CORRECT_DIAGNOSIS",
                "root_cause_id": node_id,
                "root_cause_layer": s.nodes[node_id].layer,
                "mttr_seconds": elapsed,
                "false_positives": s.false_positives,
                "note": "Correct root cause identified. Maintenance scheduled.",
            }
        else:
            s.false_positives += 1
            return -0.2, {
                "result": "WRONG_DIAGNOSIS",
                "guessed": node_id,
                "guessed_layer": s.nodes.get(node_id, NetworkNode(
                    node_id="?", layer="cell_tower"
                )).layer if node_id in s.nodes else "unknown",
                "false_positives_total": s.false_positives,
            }

    def _clear_downstream(self, node_id: str):
        """Clear all alarms downstream from a fixed node."""
        s = self._state
        queue = deque([node_id])
        while queue:
            nid = queue.popleft()
            s.nodes[nid].status = "UP"
            s.nodes[nid].alarm_text = None
            s.nodes[nid].voltage = 48.0
            queue.extend(s.nodes[nid].children)
        s.active_alarms = []

    def _build_observation(self) -> AgentObservation:
        """Build the agent-facing observation, including a network topology summary."""
        s = self._state

        # Build layer summary
        layer_counts: Counter = Counter()
        layer_alarming: Counter = Counter()
        for node in s.nodes.values():
            layer_counts[node.layer] += 1
            if node.status != "UP":
                layer_alarming[node.layer] += 1

        # Build region summary
        region_alarm_counts = {}
        for region, node_ids in s.regions.items():
            alarming = sum(1 for nid in node_ids if s.nodes[nid].status != "UP")
            region_alarm_counts[region] = {
                "total_nodes": len(node_ids),
                "alarming_nodes": alarming,
            }

        network_summary = {
            "total_nodes": len(s.nodes),
            "layers": {
                layer: {"total": layer_counts[layer], "alarming": layer_alarming[layer]}
                for layer in ["power_unit", "core_switch", "radio_controller", "cell_tower"]
                if layer_counts[layer] > 0
            },
            "regions": region_alarm_counts,
        }

        return AgentObservation(
            active_alarms=s.active_alarms[:50],  # cap to avoid token explosion
            total_alarm_count=len(s.active_alarms),
            steps_remaining=s.max_steps - s.steps_taken,
            false_positives_so_far=s.false_positives,
            checked_nodes=list(s.checked_nodes),
            episode_done=s.episode_done,
            task_description=self.task_config.description,
            network_summary=network_summary,
        )
