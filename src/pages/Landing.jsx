import { motion } from "framer-motion";
import { ArrowRight, BrainCircuit, Network, ShieldAlert, Sparkles, Waypoints } from "lucide-react";

import { TASK_METADATA } from "@/utils/constants";

const ambientNodes = [
  { id: "a", x: 10, y: 30 },
  { id: "b", x: 26, y: 56 },
  { id: "c", x: 30, y: 24 },
  { id: "d", x: 46, y: 48 },
  { id: "e", x: 58, y: 26 },
  { id: "f", x: 66, y: 60 },
  { id: "g", x: 82, y: 36 },
  { id: "h", x: 90, y: 54 },
];

const ambientEdges = [
  ["a", "b"],
  ["a", "c"],
  ["c", "d"],
  ["d", "e"],
  ["d", "f"],
  ["e", "g"],
  ["f", "g"],
  ["g", "h"],
];

function AmbientNetwork() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <svg className="h-full w-full opacity-65" viewBox="0 0 100 100" preserveAspectRatio="none">
        {ambientEdges.map(([fromId, toId]) => {
          const from = ambientNodes.find((node) => node.id === fromId);
          const to = ambientNodes.find((node) => node.id === toId);
          return (
            <motion.line
              key={`${fromId}-${toId}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              className="ambient-line"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 2.6, repeat: Infinity, repeatType: "mirror", ease: "easeInOut" }}
            />
          );
        })}

        {ambientNodes.map((node, index) => (
          <motion.circle
            key={node.id}
            cx={node.x}
            cy={node.y}
            r="1.2"
            fill={index % 3 === 0 ? "#B45C64" : index % 2 === 0 ? "#B88A6A" : "#D8D1C2"}
            animate={{
              scale: [1, 1.4, 1],
              opacity: [0.45, 1, 0.45],
            }}
            transition={{
              duration: 2.8,
              repeat: Infinity,
              ease: "easeInOut",
              delay: index * 0.18,
            }}
          />
        ))}
      </svg>
    </div>
  );
}

export function Landing({ activeTask, onSelectTask, onLaunch, loading }) {
  const features = [
    {
      icon: Network,
      title: "Alarm Propagation",
      text: "Track failure cones across physical dependencies instead of reading alarms in isolation.",
    },
    {
      icon: ShieldAlert,
      title: "Explainable RCA",
      text: "Show why a node is suspected with path convergence, topology context, and environment evidence.",
    },
    {
      icon: BrainCircuit,
      title: "Agent Operations",
      text: "Present each action like an intelligent telecom copilot making methodical operator-grade decisions.",
    },
  ];

  return (
    <main className="relative isolate mx-auto flex min-h-screen max-w-7xl flex-col justify-center px-6 py-10 lg:px-10">
      <AmbientNetwork />

      <div className="grid items-center gap-8 lg:grid-cols-[1.12fr_0.88fr]">
        <motion.section
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55, ease: "easeOut" }}
          className="relative z-10"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-cream/10 bg-black/10 px-4 py-2 text-xs uppercase tracking-[0.34em] text-sand/85">
            <Sparkles className="h-4 w-4" />
            Premium RCA Interface
          </div>

          <h1 className="mt-6 max-w-4xl font-display text-5xl font-semibold leading-[0.95] tracking-tight text-cream sm:text-6xl lg:text-7xl">
            AI-Powered
            <span className="block text-sand">Telecom Root Cause Analysis</span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-cream/72 sm:text-xl">
            A refined telecom operations experience that makes graph-based RCA immediately understandable:
            cascade visibility, agent reasoning, and operational metrics in one premium interface.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => onLaunch(activeTask)}
              disabled={loading}
              className="primary-btn"
            >
              Launch Simulation
              <ArrowRight className="h-4 w-4" />
            </button>
            <div className="control-chip">
              <Waypoints className="h-4 w-4" />
              Animated graph reasoning over live symptom alarms
            </div>
          </div>

          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {features.map((feature) => (
              <motion.div
                key={feature.title}
                whileHover={{ y: -4 }}
                className="surface-card hero-sheen p-5"
              >
                <feature.icon className="h-6 w-6 text-bronze" />
                <h2 className="mt-4 font-display text-[1.6rem] font-semibold text-cream">{feature.title}</h2>
                <p className="mt-2 text-sm leading-6 text-cream/65">{feature.text}</p>
              </motion.div>
            ))}
          </div>
        </motion.section>

        <motion.aside
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.08 }}
          className="panel-shell relative z-10 overflow-hidden p-6"
        >
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="section-title">Simulation Tasks</p>
              <p className="mt-2 font-display text-3xl font-semibold text-cream">Judge-ready scenario control</p>
            </div>
            <span className="control-chip">Live topology playback</span>
          </div>

          <div className="mt-6 space-y-4">
            {Object.entries(TASK_METADATA).map(([taskKey, meta]) => {
              const isActive = taskKey === activeTask;
              return (
                <button
                  key={taskKey}
                  type="button"
                  onClick={() => onSelectTask(taskKey)}
                  className={`w-full rounded-[1.6rem] border px-5 py-4 text-left transition duration-300 ${
                    isActive
                      ? "border-sand/45 bg-gradient-to-br from-sand/[0.18] to-bronze/10 shadow-glow"
                      : "border-cream/10 bg-black/10 hover:border-sand/20 hover:bg-cream/[0.04]"
                  }`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="soft-label">Task {meta.index}</p>
                      <h3 className="mt-2 font-display text-[1.75rem] font-semibold text-cream">{meta.title}</h3>
                    </div>
                    <span className="rounded-full border border-cream/10 bg-black/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-sand/80">
                      {meta.shortLabel}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-cream/65">{meta.operatorStory}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="surface-card">
              <p className="soft-label">Why it wins</p>
              <p className="mt-3 font-display text-2xl font-semibold text-cream">
                Immediate graph storytelling with operator-grade polish.
              </p>
            </div>
            <div className="surface-card">
              <p className="soft-label">Visual direction</p>
              <p className="mt-3 text-sm leading-7 text-cream/68">
                Deep burgundy, warm ivory, elegant contrast, and motion that feels intelligent rather than noisy.
              </p>
            </div>
          </div>
        </motion.aside>
      </div>
    </main>
  );
}
