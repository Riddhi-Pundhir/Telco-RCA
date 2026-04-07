import { Gauge, Route, Search, ShieldCheck, TriangleAlert, Zap } from "lucide-react";
import { motion } from "framer-motion";

import { formatLayerLabel, formatRegion } from "@/utils/formatters";

const actionIcons = {
  CHECK_LOGS: Search,
  CHECK_VOLTAGE: Gauge,
  TRACE_PATH: Route,
  RESTART: Zap,
  DIAGNOSE: ShieldCheck,
};

export function NodeDetailCard({ node, onAction }) {
  if (!node) {
    return null;
  }

  const data = node.data ?? node;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="pointer-events-auto absolute bottom-5 left-5 z-20 w-full max-w-sm rounded-[1.6rem] border border-cream/12 bg-[#261718]/92 p-4 shadow-panel backdrop-blur-xl"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="soft-label">Node status</p>
          <h3 className="mt-2 font-display text-[1.9rem] font-semibold text-cream">{data.node_id}</h3>
          <p className="mt-1 text-sm text-cream/62">
            {formatLayerLabel(data.layer_name)} · {formatRegion(data.region)}
          </p>
        </div>
        <div className="rounded-full border border-suspect/25 bg-suspect/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-suspect">
          {data.status_name}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-[1rem] border border-cream/10 bg-black/15 p-3">
          <p className="soft-label">Voltage</p>
          <p className="mt-2 font-display text-2xl font-semibold text-cream">{Number(data.voltage_v ?? 0).toFixed(1)}V</p>
        </div>
        <div className="rounded-[1rem] border border-cream/10 bg-black/15 p-3">
          <p className="soft-label">Temperature</p>
          <p className="mt-2 font-display text-2xl font-semibold text-cream">{Number(data.temperature_c ?? 0).toFixed(1)}°C</p>
        </div>
      </div>

      {data.alarm ? (
        <div className="mt-4 rounded-[1rem] border border-failure/20 bg-failure/[0.08] p-3">
          <div className="flex items-center gap-2">
            <TriangleAlert className="h-4 w-4 text-failure" />
            <p className="soft-label">Alarm context</p>
          </div>
          <p className="mt-2 text-sm text-cream/68">{data.alarm.message}</p>
        </div>
      ) : null}

      <div className="mt-4 grid grid-cols-2 gap-2">
        {["CHECK_LOGS", "CHECK_VOLTAGE", "TRACE_PATH", "RESTART", "DIAGNOSE"].map((action) => {
          const Icon = actionIcons[action];
          return (
            <button
              key={action}
              type="button"
              onClick={() => onAction(action, data.node_id)}
              className="secondary-btn justify-center text-xs"
            >
              <Icon className="h-4 w-4" />
              {action.replace("CHECK_", "").replace("_", " ")}
            </button>
          );
        })}
      </div>
    </motion.div>
  );
}
