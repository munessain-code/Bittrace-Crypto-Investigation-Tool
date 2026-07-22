"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import {
  api,
  CytoscapeNode,
  CytoscapeEdge,
  NodeInfo,
  mergeSubgraphs,
} from "@/lib/graph-api";
import { NodeInspector } from "@/components/NodeInspector";

const NODE_COLORS: Record<string, string> = {
  "1": "#ef4444",
  "2": "#22c55e",
  "3": "#6b7280",
};

const CLASS_LABELS: Record<string, string> = {
  "1": "illicit",
  "2": "licit",
  "3": "unknown",
};

type Mode = "idle" | "tracing" | "loading";
type ForceNode = { id: string; class?: number; timestep?: number } & Record<
  string,
  unknown
>;
type ForceLink = { source: string | { id: string }; target: string | { id: string } };

function buildTooltip(node: ForceNode): string {
  const lines: string[] = [];
  lines.push(`<b>TX ${node.id}</b>`);
  const cls = String(node.class ?? "3");
  lines.push(
    `Class: <span style="color:${NODE_COLORS[cls] || "#6b7280"}">${CLASS_LABELS[cls] ?? "unknown"}</span>`,
  );
  if (node.timestep !== undefined && node.timestep !== null)
    lines.push(`Timestep: t=${node.timestep}`);
  if (node.total_BTC !== undefined && node.total_BTC !== null)
    lines.push(`Total BTC: ${(node.total_BTC as number).toFixed(4)}`);
  if (node.fees !== undefined && node.fees !== null)
    lines.push(`Fees: ${(node.fees as number).toFixed(6)}`);
  return lines.join("<br/>");
}

function applyFilters(
  nodes: CytoscapeNode[],
  edges: CytoscapeEdge[],
  timestep: number | null,
  selectedClass: string | null,
): { nodes: CytoscapeNode[]; edges: CytoscapeEdge[] } {
  let filteredNodes = nodes;
  if (timestep !== null) {
    filteredNodes = filteredNodes.filter((n) => n.data.timestep === timestep);
  }
  if (selectedClass !== null) {
    filteredNodes = filteredNodes.filter(
      (n) => String(n.data.class ?? "3") === selectedClass,
    );
  }
  const nodeIds = new Set(filteredNodes.map((n) => n.data.id));
  const filteredEdges = edges.filter(
    (e) => nodeIds.has(e.data.source) && nodeIds.has(e.data.target),
  );
  return { nodes: filteredNodes, edges: filteredEdges };
}

function linkId(e: ForceLink): string {
  const src = typeof e.source === "object" ? e.source.id : e.source;
  const tgt = typeof e.target === "object" ? e.target.id : e.target;
  return `${src}→${tgt}`;
}

export function GraphExplorer({
  timestep,
  selectedClass,
}: {
  timestep: number | null;
  selectedClass: string | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });
  const [fullNodes, setFullNodes] = useState<CytoscapeNode[]>([]);
  const [fullEdges, setFullEdges] = useState<CytoscapeEdge[]>([]);
  const [nodes, setNodes] = useState<CytoscapeNode[]>([]);
  const [edges, setEdges] = useState<CytoscapeEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<NodeInfo | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [traceInfo, setTraceInfo] = useState<{
    direction: string;
    hopCount: number;
    edgeCount: number;
  } | null>(null);
  const [highlightNodeIds, setHighlightNodeIds] = useState<Set<string>>(new Set());
  const [highlightEdgeKeys, setHighlightEdgeKeys] = useState<Set<string>>(new Set());
  const [searchId, setSearchId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [expandDepth, setExpandDepth] = useState(2);
  const [expandBudget, setExpandBudget] = useState(500);
  const [accumulate, setAccumulate] = useState(true);

  const graphSnap = useRef({ nodes: fullNodes, edges: fullEdges });
  graphSnap.current = { nodes: fullNodes, edges: fullEdges };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      const w = Math.max(0, Math.floor(el.clientWidth));
      const h = Math.max(0, Math.floor(el.clientHeight));
      setDims((prev) =>
        prev.width === w && prev.height === h ? prev : { width: w, height: h },
      );
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const expandAround = useCallback(
    async (nodeId: number, forceReplace = false) => {
      const replace = forceReplace || !accumulate;
      setMode("loading");
      setError(null);
      try {
        const data = await api.graph.expand(nodeId, expandDepth, expandBudget);
        if (replace) {
          setFullNodes(data.nodes);
          setFullEdges(data.edges);
          setHighlightNodeIds(new Set());
          setHighlightEdgeKeys(new Set());
          setTraceInfo(null);
        } else {
          const merged = mergeSubgraphs(graphSnap.current, data);
          setFullNodes(merged.nodes);
          setFullEdges(merged.edges);
        }
        const info = await api.graph.node(nodeId);
        setSelectedNode(info);
        setMode("idle");
      } catch (e: unknown) {
        setError((e as Error).message);
        setMode("idle");
      }
    },
    [accumulate, expandDepth, expandBudget],
  );

  useEffect(() => {
    expandAround(10000476, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const filtered = applyFilters(fullNodes, fullEdges, timestep, selectedClass);
    setNodes(filtered.nodes);
    setEdges(filtered.edges);
  }, [fullNodes, fullEdges, timestep, selectedClass]);

  const runTrace = useCallback(
    async (direction: "downstream" | "upstream") => {
      if (!selectedNode) return;
      setMode("tracing");
      setError(null);
      try {
        const result = await api.graph.trace(
          selectedNode.node_id,
          direction,
          10,
        );
        const cy = result.cytoscape;
        if (accumulate) {
          const merged = mergeSubgraphs(graphSnap.current, cy);
          setFullNodes(merged.nodes);
          setFullEdges(merged.edges);
        } else {
          setFullNodes(cy.nodes);
          setFullEdges(cy.edges);
        }
        // Highlight full BFS tree (all branches), not a single linear path
        setHighlightNodeIds(new Set(result.nodes.map(String)));
        const edgeSet = new Set<string>();
        for (const e of result.edges) {
          edgeSet.add(`${e[0]}→${e[1]}`);
        }
        setHighlightEdgeKeys(edgeSet);
        const hops = Object.values(result.hops ?? {});
        setTraceInfo({
          direction,
          hopCount: hops.length ? Math.max(...hops) : 0,
          edgeCount: result.edges.length,
        });
        setMode("idle");
      } catch (e: unknown) {
        setError((e as Error).message);
        setMode("idle");
      }
    },
    [selectedNode, accumulate],
  );

  const handleNodeClick = useCallback(async (node: ForceNode) => {
    try {
      const info = await api.graph.node(Number(node.id));
      setSelectedNode(info);
    } catch {
      setSelectedNode({
        node_id: Number(node.id),
        attributes: node,
        in_degree: 0,
        out_degree: 0,
        degree: 0,
      });
    }
  }, []);

  const handleSearch = () => {
    const id = parseInt(searchId, 10);
    if (!isNaN(id)) expandAround(id, true);
  };

  const getNodeColor = (n: ForceNode) => {
    if (highlightNodeIds.has(n.id)) return "#fbbf24";
    return NODE_COLORS[String(n.class ?? "3")] ?? "#6b7280";
  };

  const getEdgeColor = (e: ForceLink) => {
    if (highlightEdgeKeys.has(linkId(e))) return "#fbbf24";
    return "rgba(255,255,255,0.1)";
  };

  return (
    <div className="flex h-full min-h-0 w-full overflow-hidden">
      <div
        ref={containerRef}
        className="relative flex-1 min-w-0 min-h-0 overflow-hidden bg-[var(--bg-primary)]"
      >
        {dims.width > 0 && dims.height > 0 && (
          <ForceGraph2D
            graphData={{
              nodes: nodes.map((n) => ({
                ...n.data,
                id: String(n.data.id),
              })),
              links: edges.map((e) => ({
                source: String(e.data.source),
                target: String(e.data.target),
              })),
            }}
            nodeColor={getNodeColor}
            linkColor={getEdgeColor}
            nodeLabel={buildTooltip}
            nodeRelSize={4}
            linkWidth={0.5}
            onNodeClick={handleNodeClick}
            backgroundColor="var(--bg-primary)"
            width={dims.width}
            height={dims.height}
          />
        )}

        <div className="absolute inset-0 pointer-events-none z-10 flex flex-col justify-between p-3 sm:p-4 gap-2 overflow-hidden">
          <div className="flex justify-between items-start gap-2 shrink-0">
            <div className="flex flex-col gap-1 max-w-sm">
              {error && (
                <div className="bg-red-900/80 text-red-200 text-xs px-3 py-2 rounded-lg pointer-events-auto">
                  {error}
                </div>
              )}
              {selectedNode &&
                (selectedNode.is_fan_out || selectedNode.out_degree > 1) && (
                  <div className="bg-orange-900/80 text-orange-100 text-xs px-3 py-1.5 rounded-lg pointer-events-auto">
                    Fan-out: {selectedNode.out_degree} outgoing TX edges —
                    Expand / Trace Down follows all branches
                  </div>
                )}
            </div>
            <div className="flex gap-1 pointer-events-auto">
              <input
                type="text"
                placeholder="TX ID…"
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="w-28 px-2 py-1 text-xs bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-lg text-white placeholder-[var(--text-secondary)]"
              />
              <button
                onClick={handleSearch}
                className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-500 rounded-lg"
              >
                Go
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-2 shrink-0">
            <div className="flex flex-wrap items-center gap-2 pointer-events-auto bg-[var(--bg-panel)]/90 border border-[var(--border-color)] rounded-lg px-2 py-1.5 text-[10px] text-[var(--text-secondary)]">
              <span className="font-semibold text-white/80">Expand</span>
              <label className="flex items-center gap-1">
                depth
                <select
                  value={expandDepth}
                  onChange={(e) => setExpandDepth(Number(e.target.value))}
                  className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-1 py-0.5 text-white"
                >
                  {[1, 2, 3, 4, 5].map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-1">
                max nodes
                <select
                  value={expandBudget}
                  onChange={(e) => setExpandBudget(Number(e.target.value))}
                  className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-1 py-0.5 text-white"
                >
                  {[100, 250, 500, 1000, 2000].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={accumulate}
                  onChange={(e) => setAccumulate(e.target.checked)}
                />
                accumulate
              </label>
              <span className="text-white/50">
                {fullNodes.length} nodes · {fullEdges.length} edges
              </span>
            </div>

            <div className="flex flex-wrap justify-between items-end gap-2">
              <div className="flex flex-wrap gap-1 pointer-events-auto">
                <button
                  onClick={() => runTrace("downstream")}
                  disabled={!selectedNode || mode === "loading"}
                  className="px-2 py-1 text-xs bg-blue-600/80 hover:bg-blue-500 disabled:opacity-30 rounded-lg"
                >
                  ▶ Trace Down
                </button>
                <button
                  onClick={() => runTrace("upstream")}
                  disabled={!selectedNode || mode === "loading"}
                  className="px-2 py-1 text-xs bg-purple-600/80 hover:bg-purple-500 disabled:opacity-30 rounded-lg"
                >
                  ◀ Trace Up
                </button>
                <button
                  onClick={() =>
                    selectedNode && expandAround(selectedNode.node_id)
                  }
                  disabled={!selectedNode || mode === "loading"}
                  className="px-2 py-1 text-xs bg-[var(--bg-panel)] border border-[var(--border-color)] hover:bg-[var(--border-color)] disabled:opacity-30 rounded-lg"
                >
                  ⊕ Expand
                </button>
                <button
                  onClick={() => {
                    setHighlightNodeIds(new Set());
                    setHighlightEdgeKeys(new Set());
                    setTraceInfo(null);
                    expandAround(10000476, true);
                  }}
                  className="px-2 py-1 text-xs bg-[var(--bg-panel)] border border-[var(--border-color)] hover:bg-[var(--border-color)] rounded-lg"
                >
                  Reset
                </button>
              </div>
              <div className="flex flex-wrap gap-2 text-[10px] text-[var(--text-secondary)] bg-[var(--bg-primary)]/70 px-2 py-1 rounded">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-red-500" /> Illicit
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500" /> Licit
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-gray-500" /> Unknown
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-yellow-400" /> Trace
                </span>
              </div>
            </div>
          </div>
        </div>

        {traceInfo && (
          <div className="absolute top-12 left-3 sm:left-4 z-20 bg-yellow-900/80 text-yellow-200 text-xs px-3 py-2 rounded-lg max-w-[min(100%,22rem)]">
            Trace {traceInfo.direction}: ≤{traceInfo.hopCount} hops ·{" "}
            {highlightNodeIds.size} nodes · {traceInfo.edgeCount} edges (all
            branches)
          </div>
        )}

        {mode === "loading" && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg-primary)]/80 z-30">
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-[var(--text-secondary)]">
                Loading subgraph…
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="w-[min(30%,360px)] min-w-[240px] max-w-[360px] shrink-0 min-h-0 overflow-hidden border-l border-[var(--border-color)]">
        <NodeInspector
          node={selectedNode}
          onTraceDown={() => runTrace("downstream")}
          onTraceUp={() => runTrace("upstream")}
          onExpand={() => selectedNode && expandAround(selectedNode.node_id)}
        />
      </div>
    </div>
  );
}
