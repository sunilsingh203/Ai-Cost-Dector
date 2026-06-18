import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import Navbar from "../components/Navbar";
import ProgressTracker from "../components/ProgressTracker";
import { api, connectProgressSocket } from "../lib/api";
import type { ResourceGroup } from "../types";

export default function Dashboard() {
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);
  const [resourceGroups, setResourceGroups] = useState<ResourceGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState("");
  const [loadingGroups, setLoadingGroups] = useState(true);
  const [running, setRunning] = useState(false);
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadGroups() {
      try {
        const data = await api.getResourceGroups();
        setResourceGroups(data.resource_groups);
        if (data.resource_groups.length > 0) {
          setSelectedGroup(data.resource_groups[0].name);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load resource groups.",
        );
      } finally {
        setLoadingGroups(false);
      }
    }

    loadGroups();

    return () => {
      socketRef.current?.close();
    };
  }, []);

  async function handleRunAnalysis() {
    if (!selectedGroup) return;

    setError("");
    setProgressMessages([]);
    setRunning(true);
    socketRef.current?.close();

    try {
      const start = await api.startAnalysis(selectedGroup);
      const analysisId = start.analysis_id;

      socketRef.current = connectProgressSocket(
        analysisId,
        (message) => {
          setProgressMessages((prev) =>
            prev[prev.length - 1] === message ? prev : [...prev, message],
          );

          if (message === "Analysis complete") {
            setRunning(false);
            navigate(`/report/${analysisId}`);
          }

          if (message.startsWith("Analysis failed")) {
            setRunning(false);
            setError(message);
          }
        },
        () => setRunning(false),
      );
    } catch (err) {
      setRunning(false);
      setError(
        err instanceof Error ? err.message : "Failed to start analysis.",
      );
    }
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="mt-2 text-slate-400">
            Select an Azure resource group and run an AI-powered cost analysis.
          </p>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Resource Group
            </label>
            <select
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              disabled={loadingGroups || running}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-indigo-500 disabled:opacity-50"
            >
              {resourceGroups.length === 0 ? (
                <option value="">
                  {loadingGroups ? "Loading..." : "No resource groups found"}
                </option>
              ) : (
                resourceGroups.map((group) => (
                  <option key={group.name} value={group.name}>
                    {group.name} ({group.location})
                  </option>
                ))
              )}
            </select>

            <button
              type="button"
              onClick={handleRunAnalysis}
              disabled={!selectedGroup || running || loadingGroups}
              className="mt-4 rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
            >
              {running ? "Running analysis..." : "Run Analysis"}
            </button>
          </div>

          {error && (
            <p className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </p>
          )}

          <ProgressTracker messages={progressMessages} isRunning={running} />
        </div>
      </main>
    </div>
  );
}
