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
    return "text-failure";
  }
  if (status === "DEGRADED") {
    return "text-suspect";
  }
  return "text-healthy";
}

export function TelecomNode({ data }) {
  const Icon = pickIcon(data.layer_name);
  const classes = [
    "telecom-node",
    data.isSelected ? "selected" : "",
    data.isSuspect ? "suspect pulse" : "",
    data.isConfirmedRoot ? "confirmed pulse" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: "none" }} />
      <div className="relative flex items-start justify-between gap-3">
        <div className="rounded-2xl border border-cream/10 bg-black/12 p-2">
          <Icon className="h-5 w-5 text-sand" />
        </div>
        <div className={`rounded-full border border-cream/10 px-2.5 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.24em] ${statusTone(data.status_name)}`}>
          {data.status_name}
        </div>
      </div>

      <p className="mt-4 text-sm font-semibold uppercase tracking-[0.22em] text-sand/65">
        {data.config?.shortLabel}
      </p>
      <p className="mt-1 text-base font-semibold text-cream">{data.node_id}</p>
      <p className="mt-2 text-sm text-cream/58">{data.config?.role}</p>

      <div className="mt-4 flex items-center justify-between text-xs text-cream/52">
        <span>{data.region}</span>
        <span>{formatPercentage(data.suspicionScore ?? 0)}</span>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: "none" }} />
    </div>
  );
}

