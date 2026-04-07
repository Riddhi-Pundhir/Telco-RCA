# Theory and Research Significance

## 1. Problem Motivation

Root cause analysis in telecom systems is difficult because the alarms operators see are usually **effects**, not **causes**. A single hardware failure can trigger a large downstream cascade: a failed power unit may surface as controller instability, transport degradation, and tower-level service alarms across multiple regions.

This is especially hard in 5G infrastructure because dependencies are deep, layered, and geographically distributed. Alarm streams are noisy, many alerts are transient or spurious, and the causal chain often spans multiple hops before the real source becomes clear. Telco-RCA is motivated by the need for environments that test **structured causal reasoning under uncertainty**, not just alarm classification.

## 2. Why This Problem is Hard

- Requires reasoning over hierarchical graphs
- High noise-to-signal ratio
- Delayed causal effects
- Partial observability with costly exploration

- **Graph reasoning:** The environment is organized as a dependency graph, not an i.i.d. dataset. The agent must infer which upstream node best explains a distributed set of downstream alarms.
- **Multi-hop dependency chains:** Failures propagate through a layered topology: Power Unit -> Core Switch -> Radio Controller -> Tower. Correct diagnosis often requires tracing across several hops rather than reacting to the loudest alarm.
- **Noisy observations:** Many alarms are intentionally non-causal. High noise means a strong local signal may still be misleading.
- **Partial observability:** The full cause is not revealed directly. Agents must actively inspect nodes, trace paths, and choose when to commit to a diagnosis.
- **Sequential decision cost:** Every unnecessary action increases MTTR and operational risk. In real networks, false positives waste engineering effort and delay restoration.

The central difficulty is recovering a hidden causal explanation from sparse local evidence while navigating a large structured search space.

## 3. Limitations of Existing Approaches

- **Rule-based alarm correlation systems** are often brittle. They work when failure patterns match hand-written templates, but degrade when topologies evolve, noise rises, or failure signatures overlap.
- **Static monitoring dashboards** provide visibility, not adaptive reasoning. They help operators inspect data, but they do not solve the exploration problem.
- **Large language models** can summarize logs well, but they often struggle with stable multi-step reasoning over large graphs.
- **Common RL benchmarks** such as gridworlds, Atari, or simple control tasks do not capture industrial causal structure, alarm ambiguity, or graph-based exploration under operational constraints.

## 4. Our Approach

Telco-RCA frames telecom debugging as an interactive graph-reasoning environment built around a realistic 4-layer topology:

- Power Units
- Core Switches
- Radio Controllers
- Cell Towers

On top of this structure, it adds:

- **Failure injection** at different infrastructure layers
- **Alarm propagation** from root cause to downstream dependents
- **Noise injection** to simulate misleading or non-causal incidents
- **Action-based exploration** through operations such as `CHECK_LOGS`, `CHECK_VOLTAGE`, `TRACE_PATH`, `RESTART`, and `DIAGNOSE`

This makes the benchmark suitable for **RL agents**, **GNN-based models**, and **hybrid systems** that combine graph structure with sequential decision-making. The key innovation is that the agent must **interact with the environment to uncover causality**.

## 5. Why This is Novel

Telco-RCA is not a toy simulator and not a generic monitoring dashboard. It is a benchmark designed around the structure of real telecom failure analysis.

Its novelty comes from combining:

- hierarchical infrastructure dependencies
- realistic cascading alarm behavior
- noisy and adversarially confusing signals
- decision-based exploration instead of one-shot prediction

This bridges the gap between synthetic RL environments and real-world industrial systems.

## 6. Real-World Relevance

In real 5G operations, Network Operations Center teams routinely face alarm storms during outages. A single upstream failure can create dozens or hundreds of alerts across radio, transport, and access layers. Human operators must inspect logs, correlate dependencies, and decide where to send repair crews.

Telco-RCA mirrors this workflow in a controlled environment. It captures the practical tension between speed and correctness:

- recover quickly
- avoid false dispatches
- reason over infrastructure dependencies
- separate symptom alarms from root cause alarms

That makes it a credible testbed for AI-assisted outage management.

## 7. Benchmark Potential

- Topology size scales from 100-node to 1000-node settings
- Difficulty scales from `easy` to `extreme`
- Performance is evaluated with operationally meaningful metrics such as MTTR, false positives, and action efficiency

This enables rigorous comparisons across agent classes. A method that performs well here must balance exploration, causal inference, and decision precision.

## 8. Future Extensions

Several extensions could make the environment even closer to production-grade benchmarking:

- multi-root failures instead of a single hidden cause
- temporal graphs with evolving topology and alarm timing
- probabilistic causality rather than deterministic propagation
- integration with real telemetry, fault logs, or OSS/BSS traces

These extensions would push Telco-RCA further toward a research benchmark for intelligent operations in complex networked systems.
