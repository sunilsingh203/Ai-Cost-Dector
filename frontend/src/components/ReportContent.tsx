function severityClass(severity: string) {
  switch (severity.toLowerCase()) {
    case "high":
      return "bg-red-500/15 text-red-400 border-red-500/30";
    case "medium":
      return "bg-amber-500/15 text-amber-400 border-amber-500/30";
    default:
      return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
  }
}

function CopyButton({ text }: { text: string }) {
  async function copy() {
    await navigator.clipboard.writeText(text);
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 transition hover:bg-slate-800"
    >
      Copy
    </button>
  );
}

interface ReportContentProps {
  resourceGroup: string;
  resourcesScanned: number;
  issuesFound: number;
  estimatedSavings: string;
  summary: string;
  issues: Array<{
    resource_name: string;
    resource_type: string;
    issue_type: string;
    severity: string;
    explanation: string;
    fix_command: string | null;
  }>;
}

export default function ReportContent({
  resourceGroup,
  resourcesScanned,
  issuesFound,
  estimatedSavings,
  summary,
  issues,
}: ReportContentProps) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-xs uppercase text-slate-500">Resource Group</p>
          <p className="mt-1 font-semibold text-white">{resourceGroup}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-xs uppercase text-slate-500">Resources Scanned</p>
          <p className="mt-1 text-2xl font-bold text-white">
            {resourcesScanned}
          </p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-xs uppercase text-slate-500">Est. Savings</p>
          <p className="mt-1 font-semibold text-emerald-400">
            {estimatedSavings}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-lg font-semibold text-white">Summary</h2>
        <p className="mt-3 text-slate-300">{summary}</p>
        <p className="mt-4 text-sm text-slate-500">
          {issuesFound} issue{issuesFound === 1 ? "" : "s"} found
        </p>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-white">Issues</h2>
        {issues.length === 0 ? (
          <p className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
            No cost issues detected.
          </p>
        ) : (
          issues.map((issue, index) => (
            <article
              key={`${issue.resource_name}-${index}`}
              className="rounded-xl border border-slate-800 bg-slate-900 p-5"
            >
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-medium text-white">{issue.resource_name}</h3>
                <span
                  className={`rounded-full border px-2 py-0.5 text-xs font-medium ${severityClass(issue.severity)}`}
                >
                  {issue.severity}
                </span>
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                  {issue.issue_type}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {issue.resource_type}
              </p>
              <p className="mt-3 text-sm text-slate-300">{issue.explanation}</p>
              {issue.fix_command && (
                <div className="mt-4 rounded-lg bg-slate-950 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs uppercase text-slate-500">
                      Fix command
                    </span>
                    <CopyButton text={issue.fix_command} />
                  </div>
                  <code className="block overflow-x-auto text-sm text-indigo-300">
                    {issue.fix_command}
                  </code>
                </div>
              )}
            </article>
          ))
        )}
      </div>
    </div>
  );
}
