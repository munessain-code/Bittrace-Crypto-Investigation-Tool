"use client";

import { useEffect, useState } from "react";
import { api, GraphOverview } from "@/lib/graph-api";

const CLASS_LABELS: Record<string, string> = {
  "1": "illicit",
  "2": "licit",
  "3": "unknown",
};

export function MacroOverview({
  onTimestepSelect,
  onClassSelect,
  onTabSelect,
}: {
  onTimestepSelect: (ts: number) => void;
  onClassSelect?: (cls: string) => void;
  onTabSelect?: () => void;
}) {
  const [data, setData] = useState<GraphOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.graph.overview().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-gray-400">Loading macro data…</div>;
  if (!data) return <div className="p-8 text-red-400">Failed to load overview</div>;

  const illicitTS = data.illicit_per_timestep;
  const maxIllicit = Math.max(...Object.values(illicitTS), 1);
  const tsKeys = Object.keys(illicitTS).sort((a, b) => Number(a) - Number(b));

  return (
    <div className="p-6 space-y-8 overflow-auto h-full">
      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Nodes" value={data.total_nodes.toLocaleString()} />
        <StatCard label="Total Edges" value={data.total_edges.toLocaleString()} />
        <StatCard label="Illicit Nodes" value={data.class_counts["1"]?.toLocaleString() ?? "—"} color="text-red-400" />
        <StatCard label="Graph Density" value={data.density.toExponential(2)} />
      </div>

      {/* Class breakdown */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-[var(--bg-panel)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">Class Distribution</h3>
          <div className="space-y-2">
            {[
              { cls: "1", label: "Illicit", color: "bg-red-500" },
              { cls: "2", label: "Licit", color: "bg-green-500" },
              { cls: "3", label: "Unknown", color: "bg-gray-500" },
            ].map(({ cls, label, color }) => {
              const count = data.class_counts[cls] ?? 0;
              const pct = data.total_nodes
                ? ((count / data.total_nodes) * 100).toFixed(1)
                : "0";
              return (
                <button
                  key={cls}
                  type="button"
                  onClick={() => {
                    onClassSelect?.(cls);
                    onTabSelect?.();
                  }}
                  className="flex items-center gap-3 w-full text-left hover:bg-[var(--bg-primary)] rounded-lg px-1 py-0.5 transition-colors"
                >
                  <div className={`w-3 h-3 rounded-full ${color}`} />
                  <span className="text-sm w-16">{label}</span>
                  <div className="flex-1 bg-[var(--bg-primary)] rounded-full h-4 overflow-hidden">
                    <div
                      className={`h-full ${color} rounded-full`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-[var(--text-secondary)] w-14 text-right">
                    {pct}%
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Class flow */}
        <div className="bg-[var(--bg-panel)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">
            Class-to-Class Flow (edges)
          </h3>
          <div className="overflow-auto max-h-48 space-y-1">
            {Object.entries(data.class_flow)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 12)
              .map(([flow, count]) => {
                const [from, to] = flow.split("→");
                const label = `${CLASS_LABELS[from] ?? from} → ${CLASS_LABELS[to] ?? to}`;
                return (
                  <div key={flow} className="flex items-center justify-between text-xs">
                    <span className="font-mono">{label}</span>
                    <span className="text-[var(--text-secondary)]">
                      {count.toLocaleString()}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      {/* Timestep heatmap */}
      <div className="bg-[var(--bg-panel)] rounded-xl p-5 border border-[var(--border-color)]">
        <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">
          Illicit Transactions per Timestep (click to explore)
        </h3>
        <div className="flex items-end gap-1 h-32">
          {tsKeys.map((ts) => {
            const count = illicitTS[ts] ?? 0;
            const pct = (count / maxIllicit) * 100;
            return (
              <button
                key={ts}
                onClick={() => {
                  onTimestepSelect(Number(ts));
                  onTabSelect?.();
                }}
                className="flex-1 bg-blue-600/40 hover:bg-blue-500/60 rounded-t transition-colors min-w-[4px]"
                style={{ height: `${Math.max(pct, 2)}%` }}
                title={`Timestep ${ts}: ${count} illicit`}
              />
            );
          })}
        </div>
        <div className="flex justify-between mt-2 text-[10px] text-[var(--text-secondary)]">
          <span>t=1</span>
          <span>t=25</span>
          <span>t=49</span>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color = "text-white" }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-[var(--bg-panel)] rounded-xl p-4 border border-[var(--border-color)]">
      <div className="text-xs text-[var(--text-secondary)]">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}
