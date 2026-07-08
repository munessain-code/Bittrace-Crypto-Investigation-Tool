"use client";

import { useState } from "react";
import { GraphExplorer } from "@/components/GraphExplorer";
import { MacroOverview } from "@/components/MacroOverview";
import { StoryPanel } from "@/components/StoryPanel";

type Tab = "macro" | "explorer" | "story";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("explorer");
  const [timestep, setTimestep] = useState<number | null>(null);

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: "explorer", label: "Explorer", icon: "🔍" },
    { key: "macro", label: "Macro", icon: "📊" },
    { key: "story", label: "Story Mode", icon: "📖" },
  ];

  return (
    <div className="flex flex-col h-screen bg-[var(--bg-primary)]">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 bg-[var(--bg-secondary)] border-b border-[var(--border-color)]">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold tracking-tight">
            <span className="text-blue-500">Bit</span>Trace
          </h1>
          <span className="text-xs text-[var(--text-secondary)] px-2 py-0.5 bg-[var(--bg-primary)] rounded-full">
            Elliptic++
          </span>
        </div>

        {/* Tabs */}
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                activeTab === tab.key
                  ? "bg-blue-600/20 text-blue-400 font-medium"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-panel)]"
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </nav>

        {/* Timestep scrubber */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-[var(--text-secondary)]">Timestep:</label>
          <input
            type="range"
            min={1}
            max={49}
            value={timestep || 1}
            onChange={(e) => setTimestep(Number(e.target.value))}
            className="w-24 accent-blue-500"
          />
          <span className="text-xs w-5 text-center font-mono">{timestep || "—"}</span>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === "macro" && (
          <MacroOverview onTimestepSelect={(ts) => { setTimestep(ts); setActiveTab("explorer"); }} />
        )}
        {activeTab === "explorer" && (
          <GraphExplorer timestep={timestep} />
        )}
        {activeTab === "story" && (
          <StoryPanel />
        )}
      </main>
    </div>
  );
}
