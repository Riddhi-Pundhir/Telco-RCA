import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, AlertTriangle, Info, RadioTower } from "lucide-react";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";

import { NodeDetailCard } from "@/components/Graph/NodeDetailCard";
import { TelecomNode } from "@/components/Graph/TelecomNode";

const nodeTypes = {
  telecomNode: TelecomNode,
};

export function GraphPanel({
  flow,
  selectedNodeId,
  setSelectedNodeId,
  observation,
  explainability,
  runtimeState,
  onAction,
}) {
  const selectedNode = useMemo(
    () => flow.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [flow.nodes, selectedNodeId],
  );

  return (
    <section className="panel-shell flex min-h-[34rem] flex-col overflow-hidden">
      <div className="panel-header">
        <div>
          <p className="section-title">Network Graph Visualization</p>
          <p className="mt-1 text-sm text-cream/60">BBU, RRU, antenna, and power dependencies in one RCA view.</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {[
            { label: "Healthy", color: "bg-healthy" },
            { label: "Suspected", color: "bg-suspect" },
            { label: "Failed", color: "bg-failure" },
          ].map((item) => (
            <span
              key={item.label}
              className="inline-flex items-center gap-2 rounded-full border border-cream/10 bg-black/10 px-3 py-1 text-xs font-semibold text-cream/70"
            >
              <span className={`h-2 w-2 rounded-full ${item.color}`} />
              {item.label}
            </span>
          ))}
        </div>
      </div>

      <div className="flow-shell telecom-grid relative flex-1">
        {flow.nodes.length ? (
          <ReactFlow
            nodes={flow.nodes}
            edges={flow.edges}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.2}
            maxZoom={1.4}
            proOptions={{ hideAttribution: true }}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
          >
            <Background gap={22} size={1} />
            <MiniMap
              pannable
              zoomable
              nodeColor={(node) => {
                if (node.data?.isConfirmedRoot) {
                  return "#F56A6A";
                }
                if (node.data?.isSuspect) {
                  return "#F2B950";
                }
                return node.data?.status_name === "FAILED"
                  ? "#F56A6A"
                  : node.data?.status_name === "DEGRADED"
                    ? "#F2B950"
                    : "#5DD39E";
              }}
            />
            <Controls showInteractive={false} />
          </ReactFlow>
        ) : (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-cream/55">
            Launch a simulation to render the live dependency graph.
          </div>
        )}

        <div className="pointer-events-none absolute left-5 top-5 z-20 grid gap-3 md:grid-cols-3">
          <div className="rounded-[1.2rem] border border-cream/12 bg-[#261718]/75 px-4 py-3 backdrop-blur-xl">
            <p className="soft-label">Graph slice</p>
            <p className="mt-2 flex items-center gap-2 text-base font-semibold text-cream">
              <RadioTower className="h-4 w-4 text-sand" />
              {observation?.graph?.nodes?.length ?? 0} visible nodes
            </p>
          </div>
          <div className="rounded-[1.2rem] border border-cream/12 bg-[#261718]/75 px-4 py-3 backdrop-blur-xl">
            <p className="soft-label">Propagation path</p>
            <p className="mt-2 flex items-center gap-2 text-base font-semibold text-cream">
              <Activity className="h-4 w-4 text-suspect" />
              {explainability?.propagationPath?.length ?? 0} hops
            </p>
          </div>
          <div className="rounded-[1.2rem] border border-cream/12 bg-[#261718]/75 px-4 py-3 backdrop-blur-xl">
            <p className="soft-label">False positives</p>
            <p className="mt-2 flex items-center gap-2 text-base font-semibold text-cream">
              <AlertTriangle className="h-4 w-4 text-failure" />
              {runtimeState?.false_positives ?? 0}
            </p>
          </div>
        </div>

        <AnimatePresence>
          {selectedNode ? <NodeDetailCard node={selectedNode} onAction={onAction} /> : null}
        </AnimatePresence>

        {!selectedNode && flow.nodes.length ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="pointer-events-none absolute bottom-5 left-5 z-20 flex items-center gap-3 rounded-full border border-cream/12 bg-[#261718]/75 px-4 py-2 text-sm text-cream/65 backdrop-blur-xl"
          >
            <Info className="h-4 w-4 text-sand" />
            Click a node to inspect status and run RCA actions.
          </motion.div>
        ) : null}
      </div>
    </section>
  );
}

