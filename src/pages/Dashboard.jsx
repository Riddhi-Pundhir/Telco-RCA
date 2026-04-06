import { AlarmPanel } from "@/components/AlarmPanel/AlarmPanel";
import { AgentPanel } from "@/components/AgentPanel/AgentPanel";
import { ExplainabilityPanel } from "@/components/ExplainabilityPanel";
import { GraphPanel } from "@/components/Graph/GraphPanel";
import { MetricsPanel } from "@/components/Metrics/MetricsPanel";
import { TaskSelector } from "@/components/TaskSelector";

export function Dashboard({
  task,
  tasks,
  observation,
  runtimeState,
  grade,
  filteredAlarms,
  explainability,
  flow,
  metricsHistory,
  transcript,
  latestAction,
  latestInfo,
  selectedNodeId,
  setSelectedNodeId,
  showNoise,
  setShowNoise,
  isLoading,
  isRunningAgent,
  error,
  socketStatus,
  resetCurrentSimulation,
  executeAction,
  stepAgent,
  runAgent,
  onReturnToLanding,
}) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1660px] flex-col gap-4 px-4 py-4 lg:px-6">
      <TaskSelector
        task={task}
        tasks={tasks}
        observation={observation}
        runtimeState={runtimeState}
        grade={grade}
        socketStatus={socketStatus}
        isLoading={isLoading}
        isRunningAgent={isRunningAgent}
        showNoise={showNoise}
        onTaskChange={resetCurrentSimulation}
        onReset={resetCurrentSimulation}
        onRun={runAgent}
        onStep={stepAgent}
        onReturn={onReturnToLanding}
        onToggleNoise={() => setShowNoise((current) => !current)}
      />

      <div className="grid min-h-[calc(100vh-16rem)] gap-4 xl:grid-cols-[320px_minmax(0,1fr)_360px] xl:grid-rows-[minmax(0,1fr)_22rem]">
        <div className="xl:row-span-2">
          <AlarmPanel
            alarms={filteredAlarms}
            totalAlarmCount={observation?.total_alarm_count ?? 0}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
          />
        </div>

        <GraphPanel
          flow={flow}
          selectedNodeId={selectedNodeId}
          setSelectedNodeId={setSelectedNodeId}
          observation={observation}
          explainability={explainability}
          runtimeState={runtimeState}
          onAction={(actionType, nodeId) =>
            executeAction({
              actionType,
              targetNodeId: nodeId,
              source: "manual",
            })
          }
        />

        <AgentPanel
          transcript={transcript}
          latestAction={latestAction}
          latestInfo={latestInfo}
          error={error}
          isRunningAgent={isRunningAgent}
        />

        <div className="grid gap-4 xl:col-span-2 lg:grid-cols-[1.2fr_1fr]">
          <ExplainabilityPanel explainability={explainability} />
          <MetricsPanel
            metricsHistory={metricsHistory}
            runtimeState={runtimeState}
            observation={observation}
            grade={grade}
          />
        </div>
      </div>
    </main>
  );
}
