"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { MacroOverview } from "@/components/MacroOverview";

// Dynamically import graph-dependent components (no SSR)
const GraphExplorer = dynamic(
  () => import("@/components/GraphExplorer").then((m) => m.GraphExplorer),
  { ssr: false, loading: () => <div className="p-8 text-center text-zinc-500">Loading graph…</div> },
);
const GraphExplorer3D = dynamic(
  () => import("@/components/GraphExplorer3D").then((m) => m.GraphExplorer3D),
  { ssr: false, loading: () => <div className="p-8 text-center text-zinc-500">Loading 3D graph…</div> },
);
const StoryPanel = dynamic(
  () => import("@/components/StoryPanel").then((m) => m.StoryPanel),
  { ssr: false, loading: () => <div className="p-8 text-center text-zinc-500">Loading stories…</div> },
);

type Tab = "explorer" | "macro" | "story";
type ViewMode = "2d" | "3d";

export default function Home() {
  const [tab, setTab] = useState<Tab>("explorer");
  const [viewMode, setViewMode] = useState<ViewMode>("2d");
  const [selectedTime, setSelectedTime] = useState<number | null>(null);
  const [selectedClass, setSelectedClass] = useState<string | null>(null);

  return (
    <div className="flex flex-col h-screen bg-background text-primary font-sans overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-surface border-b border-border">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-accent">BitTrace</span>
          <span className="text-xs text-muted px-2 py-0.5 bg-slate-800 rounded-full">
            Graph Explorer
          </span>
        </div>
        <nav className="flex gap-1 bg-slate-800 p-1 rounded-lg">
          {(["explorer", "macro", "story"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === t
                  ? "bg-accent text-accent-foreground"
                  : "text-muted hover:text-primary"
              }`}
            >
              {t === "explorer" && "🔍 Explorer"}
              {t === "macro" && "📊 Macro"}
              {t === "story" && "📖 Story Mode"}
            </button>
          ))}
        </nav>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {tab === "explorer" && (
          <>
            {/* 2D/3D toggle bar */}
            <div className="flex items-center gap-2 px-4 py-1.5 bg-surface border-b border-border">
              <button
                onClick={() => setViewMode("2d")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  viewMode === "2d"
                    ? "bg-blue-600 text-white"
                    : "text-muted hover:text-primary hover:bg-slate-700"
                }`}
              >
                2D View
              </button>
              <button
                onClick={() => setViewMode("3d")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  viewMode === "3d"
                    ? "bg-purple-600 text-white"
                    : "text-muted hover:text-primary hover:bg-slate-700"
                }`}
              >
                3D View
              </button>
            </div>
            {viewMode === "2d" ? (
              <GraphExplorer
                timestep={selectedTime}
                selectedClass={selectedClass}
              />
            ) : (
              <GraphExplorer3D
                timestep={selectedTime}
                selectedClass={selectedClass}
              />
            )}
          </>
        )}
        {tab === "macro" && (
          <div className="h-full">
            <MacroOverview
              onTimestepSelect={setSelectedTime}
              onClassSelect={setSelectedClass}
              onTabSelect={() => setTab("explorer")}
            />
          </div>
        )}
        {tab === "story" && (
          <div className="h-full">
            <StoryPanel />
          </div>
        )}
      </main>
    </div>
  );
}
