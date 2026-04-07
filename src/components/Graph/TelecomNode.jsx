import { BatteryCharging, Cpu, RadioTower, Server } from "lucide-react";
import { Handle, Position } from "reactflow";

import { formatPercentage } from "@/utils/formatters";

function pickIcon(layer) {
  if (layer === "power_unit") {
    return BatteryCharging;
  }
  if (layer === "core_switch") {
    return Server;
  }
  if (layer === "radio_controller") {
    return Cpu;
  }
  return RadioTower;
}

function statusTone(status) {
  if (status === "FAILED") {
    return "border-failure/30 bg-failure/20 text-black";
  }
  if (status === "DEGRADED") {
    return "border-suspect/30 bg-suspect/20 text-black";
  }
  return "border-black/10 bg-black/5 text-black";
}

export function TelecomNode({ data }) {
  const Icon = pickIcon(data.layer_name);
  const classes = [
    "telecom-node",
    data.isSelected ? "selected" : "",
    data.isHighlighted ? "highlighted" : "",
    data.isSuspect ? "suspect pulse" : "",
    data.isConfirmedRoot ? "confirmed pulse" : "",
    data.isTrajectoryPath ? "trajectory-path" : "",
    data.isTrajectoryHit ? "trajectory-hit" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0, pointerEvents: "none" }} />
      <div className="relative flex items-start justify-between gap-3">
        <div className="rounded-2xl border border-black/10 bg-black/5 p-2">
          <Icon className="h-5 w-5 text-black/80" />
        </div>
        <div className={`rounded-full border px-2.5 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.24em] ${statusTone(data.status_name)}`}>
          {data.status_name}
        </div>
      </div>

      <p className="mt-4 text-sm font-semibold uppercase tracking-[0.22em] text-black/70">
        {data.config?.shortLabel}
      </p>
      <p className="break-anywhere mt-1 font-display text-[1.9rem] font-semibold leading-none text-black">
        {data.node_id}
      </p>
      <p className="break-anywhere mt-2 text-sm text-black/70">{data.config?.role}</p>

      <div className="mt-4 flex items-center justify-between text-xs text-black/60">
        <span>{data.region}</span>
        <span>{formatPercentage(data.suspicionScore ?? 0)}</span>
      </div>
      {data.trajectoryVisitCount ? (
        <div className="mt-3 flex justify-between">
          <span className="rounded-full border border-black/10 bg-black/5 px-2.5 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-black/70">
            Trajectory
          </span>
          <span className="rounded-full border border-black/10 bg-black/5 px-2.5 py-1 text-[0.75rem] font-semibold text-black/70">
            x{Number(data.trajectoryVisitCount).toFixed(1).replace(/\.0$/, "")}
          </span>
        </div>
      ) : null}
      <Handle type="source" position={Position.Right} style={{ opacity: 0, pointerEvents: "none" }} />
    </div>
  );
}
