import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Navbar from "../components/Navbar";
import ReportContent from "../components/ReportContent";
import { api } from "../lib/api";
import type { AnalysisRecord } from "../types";

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const [record, setRecord] = useState<AnalysisRecord | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!id) return;
      try {
        const data = await api.getAnalysis(Number(id));
        setRecord(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load analysis.",
        );
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [id]);

  const analysis = record?.analysis_result;
  const hasAnalysis =
    analysis && "analysis" in analysis && analysis.analysis !== undefined;

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Analysis Report</h1>
            <p className="mt-2 text-slate-400">
              AI-generated cost optimization findings
            </p>
          </div>
          <Link
            to="/history"
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
          >
            View history
          </Link>
        </div>

        {loading && (
          <p className="text-slate-400">Loading report...</p>
        )}

        {error && (
          <p className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </p>
        )}

        {record && record.status === "in_progress" && (
          <p className="rounded-lg bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
            Analysis is still running. Refresh in a moment.
          </p>
        )}

        {record && record.status === "failed" && (
          <p className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
            Analysis failed:{" "}
            {"error" in (record.analysis_result ?? {})
              ? (record.analysis_result as { error: string }).error
              : "Unknown error"}
          </p>
        )}

        {record && hasAnalysis && (
          <ReportContent
            resourceGroup={record.resource_group}
            resourcesScanned={record.resources_scanned}
            issuesFound={record.issues_found}
            estimatedSavings={
              record.estimated_savings ??
              analysis.analysis.estimated_savings ??
              "N/A"
            }
            summary={analysis.analysis.summary}
            issues={analysis.analysis.issues}
          />
        )}
      </main>
    </div>
  );
}
