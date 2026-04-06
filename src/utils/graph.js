import { LAYER_CONFIG } from "@/utils/constants";

function createPositions(nodes = []) {
  const groupedByDepth = new Map();
  const regions = [...new Set(nodes.map((node) => node.region))].sort();

  for (const node of nodes) {
    if (!groupedByDepth.has(node.depth)) {
      groupedByDepth.set(node.depth, []);
    }
    groupedByDepth.get(node.depth).push(node);
  }

  const positions = new Map();

  [...groupedByDepth.entries()]
    .sort((left, right) => left[0] - right[0])
    .forEach(([depth, depthNodes]) => {
      const ordered = [...depthNodes].sort((left, right) => {
        const regionDelta = regions.indexOf(left.region) - regions.indexOf(right.region);
        if (regionDelta !== 0) {
          return regionDelta;
        }
        return left.node_id.localeCompare(right.node_id);
      });

      const laneHeights = new Map();
      ordered.forEach((node) => {
        const regionIndex = Math.max(regions.indexOf(node.region), 0);
        const laneCount = laneHeights.get(regionIndex) ?? 0;
        const y = 110 + laneCount * (depth >= 3 ? 68 : 88) + regionIndex * 42;
        const x = 110 + depth * 250 + regionIndex * 28;
        positions.set(node.node_id, { x, y });
        laneHeights.set(regionIndex, laneCount + 1);
      });
    });

  return positions;
}

function isPropagationEdge(edge, propagationPath) {
  for (let index = 0; index < propagationPath.length - 1; index += 1) {
    if (propagationPath[index] === edge.target_id && propagationPath[index + 1] === edge.source_id) {
      return true;
    }
  }
  return false;
}

export function buildFlowElements({ graph, activeAlarms = [], explainability, selectedNodeId, state }) {
  if (!graph?.nodes?.length) {
    return { nodes: [], edges: [], nodeMap: new Map() };
  }

  const alarmMap = new Map(activeAlarms.map((alarm) => [alarm.node_id, alarm]));
  const positions = createPositions(graph.nodes);
  const nodeMap = new Map(graph.nodes.map((node) => [node.node_id, node]));
  const confirmedRootId =
    state?.episode_done && (state?.diagnosed_nodes?.includes?.(state.root_cause_id) || state?.restarted_nodes?.includes?.(state.root_cause_id))
      ? state.root_cause_id
      : null;

  const nodes = graph.nodes.map((node) => {
    const suspect = explainability?.primaryCandidate?.nodeId === node.node_id;
    const alarm = alarmMap.get(node.node_id);
    return {
      id: node.node_id,
      type: "telecomNode",
      position: positions.get(node.node_id) ?? { x: 0, y: 0 },
      data: {
        ...node,
        alarm,
        config: LAYER_CONFIG[node.layer_name],
        isSelected: selectedNodeId === node.node_id,
        isSuspect: suspect,
        isConfirmedRoot: confirmedRootId === node.node_id,
        suspicionScore: explainability?.candidates?.find((candidate) => candidate.nodeId === node.node_id)?.confidence ?? 0,
      },
    };
  });

  const edges = (graph.edges ?? []).map((edge) => {
    const animated =
      isPropagationEdge(edge, explainability?.propagationPath ?? []) ||
      alarmMap.has(edge.source_id) ||
      alarmMap.has(edge.target_id);

    const onCriticalPath = isPropagationEdge(edge, explainability?.propagationPath ?? []);
    return {
      id: `${edge.source_id}-${edge.target_id}`,
      source: edge.source_id,
      target: edge.target_id,
      type: "smoothstep",
      animated,
      style: {
        stroke: onCriticalPath ? "#E8D1C5" : animated ? "#F2B950" : "rgba(243, 232, 223, 0.16)",
        strokeWidth: onCriticalPath ? 2.5 : animated ? 1.8 : 1.2,
      },
    };
  });

  return { nodes, edges, nodeMap };
}

