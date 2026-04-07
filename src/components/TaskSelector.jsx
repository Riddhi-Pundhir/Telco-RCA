import { Activity, ArrowLeft, Bot, Play, RefreshCw, SlidersHorizontal, StepForward } from "lucide-react";

import { TASK_METADATA } from "@/utils/constants";
import { formatPercentage, formatSimTime } from "@/utils/formatters";

export function TaskSelector({
  task,
  tasks,
  observation,
  runtimeState,
  grade,
  socketStatus,
  isLoading,
  isRunningAgent,
  showNoise,
  onTaskChange,
  onReset,
  onRun,
  onStep,
  onReturn,
  onToggleNoise,
}) {
  const taskCards = tasks.length
    ? tasks.map((entry) => ({
        key: entry.name,
        title: TASK_METADATA[entry.name]?.title ?? entry.name,
        description: entry.description,
      }))
    : Object.entries(TASK_METADATA).map(([key, value]) => ({
        key,
        title: value.title,
        description: value.operatorStory,
      }));

  return (
    <header className="panel-shell p-5">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={onReturn} className="ghost-btn">
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            <div>
              <p className="section-title">Telco-RCA Mission Control</p>
              <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight text-cream">
                AI agent reasoning for 5G outage isolation
              </h1>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            {taskCards.map((entry) => {
              const active = entry.key === task;
              return (
                <button
                  key={entry.key}
                  type="button"
                  onClick={() => onTaskChange(entry.key)}
                  className={`rounded-[1.35rem] border px-4 py-3 text-left transition duration-300 ${
                    active
                      ? "border-sand/45 bg-gradient-to-br from-sand/20 to-bronze/10 shadow-glow"
                      : "border-cream/10 bg-black/10 hover:border-sand/20 hover:bg-cream/[0.04]"
                  }`}
                >
                  <p className="soft-label">{entry.key}</p>
                  <p className="mt-1 font-display text-2xl font-semibold text-cream">{entry.title}</p>
                  <p className="mt-1 text-sm text-cream/60">{entry.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-3 xl:items-end">
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => onReset(task)} disabled={isLoading} className="secondary-btn">
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Reset Simulation
            </button>
            <button
              type="button"
              onClick={onStep}
              disabled={isLoading || !observation}
              className="secondary-btn"
            >
              <StepForward className="h-4 w-4" />
              Next Step
            </button>
            <button
              type="button"
              onClick={onRun}
              disabled={isLoading || isRunningAgent || !observation}
              className="primary-btn"
            >
              <Play className="h-4 w-4" />
              {isRunningAgent ? "Running..." : "Run Agent"}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={onToggleNoise} className="control-chip">
              <SlidersHorizontal className="h-4 w-4" />
              {showNoise ? "Noise Visible" : "Noise Filtered"}
            </button>
            <span className="control-chip">
              <Activity className="h-4 w-4" />
              {socketStatus}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        <div className="stat-card">
          <p className="soft-label">Simulation time</p>
          <p className="mt-2 font-display text-3xl font-semibold text-cream">
            {formatSimTime(observation?.simulation_time_s ?? runtimeState?.simulation_time_s)}
          </p>
        </div>
        <div className="stat-card">
          <p className="soft-label">Alarm volume</p>
          <p className="mt-2 font-display text-3xl font-semibold text-cream">{observation?.total_alarm_count ?? 0}</p>
        </div>
        <div className="stat-card">
          <p className="soft-label">Steps used</p>
          <p className="mt-2 font-display text-3xl font-semibold text-cream">
            {runtimeState?.steps_taken ?? 0}
            <span className="text-base text-cream/55">
              {" "}
              / {(runtimeState?.steps_taken ?? 0) + (observation?.steps_remaining ?? 0)}
            </span>
          </p>
        </div>
        <div className="stat-card">
          <p className="soft-label">Judge projection</p>
          <p className="mt-2 flex items-center gap-2 font-display text-3xl font-semibold text-cream">
            <Bot className="h-5 w-5 text-bronze" />
            {formatPercentage(grade?.score ?? 0)}
          </p>
        </div>
      </div>
    </header>
  );
}
