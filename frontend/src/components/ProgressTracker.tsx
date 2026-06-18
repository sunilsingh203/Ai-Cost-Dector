interface ProgressTrackerProps {
  messages: string[];
  isRunning: boolean;
}

export default function ProgressTracker({
  messages,
  isRunning,
}: ProgressTrackerProps) {
  if (messages.length === 0 && !isRunning) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
        Analysis Progress
      </h3>
      <ol className="space-y-3">
        {messages.map((message, index) => {
          const isLatest = index === messages.length - 1;
          const isComplete = message === "Analysis complete";
          const isFailed = message.startsWith("Analysis failed");

          return (
            <li key={`${message}-${index}`} className="flex items-start gap-3">
              <span
                className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs ${
                  isFailed
                    ? "bg-red-500/20 text-red-400"
                    : isComplete
                      ? "bg-emerald-500/20 text-emerald-400"
                      : isLatest && isRunning
                        ? "bg-indigo-500/20 text-indigo-400"
                        : "bg-slate-700 text-slate-300"
                }`}
              >
                {isFailed ? "!" : isComplete ? "✓" : index + 1}
              </span>
              <span
                className={`text-sm ${
                  isLatest ? "text-white" : "text-slate-400"
                }`}
              >
                {message}
              </span>
            </li>
          );
        })}
      </ol>
      {isRunning && (
        <div className="mt-4 h-1 overflow-hidden rounded-full bg-slate-800">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-indigo-500" />
        </div>
      )}
    </div>
  );
}
