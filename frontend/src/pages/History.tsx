import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Navbar from "../components/Navbar";
import { api } from "../lib/api";
import type { AnalysisRecord } from "../types";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function History() {
  const [history, setHistory] = useState<AnalysisRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getHistory();
        setHistory(data.history);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load history.",
        );
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Analysis History</h1>
          <p className="mt-2 text-slate-400">
            Review past cost analyses and open full reports.
          </p>
        </div>

        {loading && <p className="text-slate-400">Loading history...</p>}

        {error && (
          <p className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </p>
        )}

        {!loading && history.length === 0 && (
          <p className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
            No analyses yet. Run your first scan from the dashboard.
          </p>
        )}

        <div className="space-y-3">
          {history.map((item) => (
            <Link
              key={item.id}
              to={`/report/${item.id}`}
              className="block rounded-xl border border-slate-800 bg-slate-900 p-5 transition hover:border-indigo-500/50 hover:bg-slate-900/80"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-white">
                    {item.resource_group}
                  </h2>
                  <p className="mt-1 text-sm text-slate-400">
                    {formatDate(item.created_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-4 text-sm">
                  <span className="text-slate-300">
                    {item.issues_found} issues
                  </span>
                  <span className="text-emerald-400">
                    {item.estimated_savings ?? "N/A"}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      item.status === "complete"
                        ? "bg-emerald-500/15 text-emerald-400"
                        : item.status === "failed"
                          ? "bg-red-500/15 text-red-400"
                          : "bg-amber-500/15 text-amber-400"
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
