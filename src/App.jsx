import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

import { Dashboard } from "@/pages/Dashboard";
import { Landing } from "@/pages/Landing";
import { useSimulation } from "@/hooks/useSimulation";

export default function App() {
  const simulation = useSimulation();
  const [view, setView] = useState("landing");

  const handleLaunch = async (task) => {
    setView("dashboard");
    await simulation.resetCurrentSimulation(task);
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-espresso text-cream">
      <div className="pointer-events-none absolute inset-0 bg-mesh opacity-90" />
      <div className="pointer-events-none absolute inset-0 noise-pattern opacity-40" />

      <AnimatePresence mode="wait">
        {view === "landing" ? (
          <motion.div
            key="landing"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -18 }}
            transition={{ duration: 0.45, ease: "easeOut" }}
          >
            <Landing
              activeTask={simulation.task}
              onSelectTask={simulation.setTask}
              onLaunch={handleLaunch}
              loading={simulation.isLoading}
            />
          </motion.div>
        ) : (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -22 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            <Dashboard
              {...simulation}
              onReturnToLanding={() => {
                simulation.stopAgent();
                setView("landing");
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

