import { motion } from "framer-motion";
import { BrainCircuit, GitBranchPlus, MapPinned, Radar } from "lucide-react";

import { formatLayerLabel, formatPercentage } from "@/utils/formatters";

export function ExplainabilityPanel({ explainability }) {
  return (
    <section className="panel-shell flex h-full flex-col">
      <div className="panel-header">
        <div>
          <p className="section-title">Explainability Panel</p>
          <p className="mt-1 text-sm text-cream/60">Why the agent believes this node is the root cause.</p>
        </div>
        <div className="rounded-full border border-sand/25 bg-sand/10 px-3 py-1 text-sm font-semibold text-sand">
          {formatPercentage(explainability?.confidence ?? 0)} confidence
        </div>
      </div>

      <div className="grid flex-1 gap-4 p-5 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-4">
          <div className="surface-card">
            <div className="flex items-center gap-3">
              <BrainCircuit className="h-5 w-5 text-bronze" />
              <div>
                <p className="soft-label">Primary suspect</p>
                <p className="mt-1 font-display text-[1.9rem] font-semibold text-cream">
                  {explainability?.primaryCandidate?.nodeId ?? "Awaiting topology"}
                </p>
              </div>
            </div>
            <p className="mt-3 text-sm text-cream/68">
              {explainability?.primaryCandidate
                ? `${formatLayerLabel(explainability.primaryCandidate.node?.layer_name)} in ${explainability.primaryCandidate.region}`
              : "Load a simulation to start RCA scoring."}
            </p>
          </div>

          <div className="surface-card">
            <div className="flex items-center gap-3">
              <GitBranchPlus className="h-5 w-5 text-suspect" />
              <div>
                <p className="soft-label">Propagation path</p>
                <p className="mt-1 text-sm text-cream/70">
                  {explainability?.propagationPath?.length
                    ? explainability.propagationPath.join("  →  ")
                    : "No propagation path available yet."}
                </p>
              </div>
            </div>
          </div>

          <div className="surface-card">
            <div className="flex items-center gap-3">
              <Radar className="h-5 w-5 text-healthy" />
              <div>
                <p className="soft-label">Reasoning trace</p>
                <div className="mt-3 space-y-2">
                  {(explainability?.reasoning ?? []).map((reason) => (
                    <p key={reason} className="text-sm text-cream/68">
                      {reason}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="surface-card">
            <div className="flex items-center gap-3">
              <MapPinned className="h-5 w-5 text-bronze" />
              <div>
                <p className="soft-label">Impacted regions</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(explainability?.impactedRegions ?? []).map((region) => (
                    <span
                      key={region}
                      className="rounded-full border border-cream/10 bg-cream/5 px-3 py-1 text-xs font-semibold text-cream/75"
                    >
                      {region}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="surface-card">
            <p className="soft-label">Top candidates</p>
            <div className="mt-4 space-y-3">
              {(explainability?.candidates ?? []).map((candidate, index) => (
                <motion.div
                  key={candidate.nodeId}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.08 }}
                  className="rounded-[1.2rem] border border-cream/10 bg-cream/[0.06] p-3"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-display text-2xl font-semibold text-cream">{candidate.nodeId}</p>
                      <p className="text-xs uppercase tracking-[0.22em] text-sand/65">
                        {candidate.label}
                      </p>
                    </div>
                    <span className="rounded-full bg-black/20 px-3 py-1 text-xs font-semibold text-sand">
                      {formatPercentage(candidate.confidence)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-cream/65">{candidate.reasons[0]}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
