"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { api, CytoscapeNode, CytoscapeEdge, StoryDetail, StorySummary } from "@/lib/graph-api";

const DIFFICULTY_COLORS: Record<string, string> = {
  EASY: "bg-green-500/20 text-green-400 border-green-500/40",
  AVERAGE: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  HARD: "bg-red-500/20 text-red-400 border-red-500/40",
  easy: "bg-green-500/20 text-green-400 border-green-500/40",
  average: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  hard: "bg-red-500/20 text-red-400 border-red-500/40",
};

const NODE_COLORS: Record<string, string> = {
  "1": "#ef4444",
  "2": "#22c55e",
  "3": "#6b7280",
};

type ForceNode = { id: string; class?: number };

export function StoryPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });
  const [stories, setStories] = useState<StorySummary[]>([]);
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [graphNodes, setGraphNodes] = useState<CytoscapeNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<CytoscapeEdge[]>([]);
  const [highlightIds, setHighlightIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () =>
      setDims({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    api.stories.list().then(setStories).catch((e) => setError((e as Error).message));
  }, []);

  const selectStory = useCallback(
    async (id: string) => {
      setLoading(true);
      setError(null);
      try {
        const [detail, subgraph] = await Promise.all([
          api.stories.get(id),
          api.graph.subgraph(id),
        ]);
        setStory(detail);
        setGraphNodes(subgraph.nodes);
        setGraphEdges(subgraph.edges);
        setCurrentStep(0);
        const firstStep = detail.steps?.[0];
        if (firstStep?.highlight_nodes) {
          setHighlightIds(new Set(firstStep.highlight_nodes.map(String)));
        }
      } catch (e: unknown) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const goStep = useCallback(
    (stepNum: number) => {
      if (!story) return;
      setCurrentStep(stepNum);
      const step = story.steps[stepNum];
      if (step?.highlight_nodes) {
        setHighlightIds(new Set(step.highlight_nodes.map(String)));
      } else {
        setHighlightIds(new Set());
      }
    },
    [story],
  );

  const getNodeColor = (n: ForceNode) => {
    if (highlightIds.has(n.id)) return "#fbbf24";
    const cls = String(n.class ?? "3");
    return NODE_COLORS[cls] ?? "#6b7280";
  };

  return (
    <div className="flex h-full">
      <div className="w-[40%] min-w-[320px] flex flex-col bg-[var(--bg-panel)] border-r border-[var(--border-color)]">
        <div className="p-4 border-b border-[var(--border-color)]">
          <h2 className="text-sm font-bold mb-3">Investigation Stories</h2>
          <div className="space-y-2 max-h-40 overflow-auto">
            {stories.map((s) => (
              <button
                key={s.id}
                onClick={() => selectStory(s.id)}
                disabled={loading}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                  story?.id === s.id
                    ? "bg-blue-600/20 text-blue-400 border border-blue-500/40"
                    : "bg-[var(--bg-primary)] hover:bg-[var(--border-color)] border border-transparent"
                }`}
              >
                <div className="font-medium">{s.title}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] border ${
                      DIFFICULTY_COLORS[s.difficulty] ?? ""
                    }`}
                  >
                    {s.difficulty}
                  </span>
                  <span className="text-[var(--text-secondary)]">{s.pattern}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {story && (
          <div className="flex-1 p-4 overflow-auto space-y-4">
            <div className="text-xs leading-relaxed text-[var(--text-secondary)]">
              {story.narrative}
            </div>

            <div className="space-y-2">
              {story.steps.map((step, i) => (
                <button
                  key={i}
                  onClick={() => goStep(i)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                    i === currentStep
                      ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/40"
                      : "bg-[var(--bg-primary)] hover:bg-[var(--border-color)] border border-transparent"
                  }`}
                >
                  <div className="font-medium">
                    Step {step.step_num}: {step.title}
                  </div>
                  <div className="text-[var(--text-secondary)] mt-1">
                    {step.description.slice(0, 120)}…
                  </div>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => goStep(Math.max(0, currentStep - 1))}
                disabled={currentStep === 0}
                className="px-3 py-1.5 text-xs bg-[var(--bg-primary)] hover:bg-[var(--border-color)] disabled:opacity-30 rounded-lg"
              >
                ← Prev
              </button>
              <span className="text-xs text-[var(--text-secondary)] flex-1 text-center">
                Step {currentStep + 1} of {story.steps.length}
              </span>
              <button
                onClick={() =>
                  goStep(Math.min(story.steps.length - 1, currentStep + 1))
                }
                disabled={currentStep === story.steps.length - 1}
                className="px-3 py-1.5 text-xs bg-[var(--bg-primary)] hover:bg-[var(--border-color)] disabled:opacity-30 rounded-lg"
              >
                Next →
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 text-xs text-red-400 bg-red-900/20 border-t border-red-500/20">
            {error}
          </div>
        )}
      </div>

      <div ref={containerRef} className="relative flex-1 bg-[var(--bg-primary)]">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg-primary)]/80 z-20">
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-[var(--text-secondary)]">
                Loading story…
              </span>
            </div>
          </div>
        )}

        {!story && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-[var(--text-secondary)] text-sm">
            Select a story to begin the investigation
          </div>
        )}

        {story && (
          <ForceGraph2D
            graphData={{
              nodes: graphNodes.map((n) => ({
                ...n.data,
                id: String(n.data.id),
              })),
              links: graphEdges.map((e) => ({
                source: String(e.data.source),
                target: String(e.data.target),
              })),
            }}
            nodeColor={getNodeColor}
            linkColor={() => "rgba(255,255,255,0.12)"}
            nodeLabel="id"
            nodeRelSize={4}
            linkWidth={0.5}
            backgroundColor="var(--bg-primary)"
            width={dims.width}
            height={dims.height}
          />
        )}

        <div className="absolute bottom-4 right-4 z-10 flex gap-2 text-[10px] text-[var(--text-secondary)]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Illicit
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" /> Licit
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-yellow-400" /> Highlighted
          </span>
        </div>
      </div>
    </div>
  );
}