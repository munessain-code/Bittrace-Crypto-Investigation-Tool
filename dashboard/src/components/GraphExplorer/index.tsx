"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { api, CytoscapeNode, CytoscapeEdge, NodeInfo, TraceResult } from "@/lib/graph-api";
import { NodeInspector } from "@/components/NodeInspector";

const CLASS_COLORS: Record<string, string> = {
  illicit: "#ef4444",
  licit: "#22c55e",
  unknown: "#6b7280",
};

const NODE_COLORS: Record<string, string> = {
  "1": "#ef4444",
  "2": "#22c55e",
  "3": "#6b7280",
};

type Mode = "idle" | "tracing" | "loading";

export function GraphExplorer({ timestep }: { timestep: number | null }) {
  const fgRef = useRef<import("react-force-graph-2d").ForceGraph2DInstance>(null);
  const [nodes, setNodes] = useState<CytoscapeNode[]>([]);
  const [edges, setEdges] = useState<CytoscapeEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<NodeInfo | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [traceInfo, setTraceInfo] = useState<{
    direction: string;
    hopCount: number;
  } | null>(null);
  const [highlightNodeIds, setHighlightNodeIds] = useState<Set<string>>(new Set());
  const [highlightEdgeKeys, setHighlightEdgeKeys] = useState<Set<string>>(new Set());
  const [searchId, setSearchId] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Load initial subgraph on mount
  useEffect(() => {
    loadExpand(10000476, 2);
  }, []);

  // Filter by timestep
  useEffect(() => {
    if (timestep) {
      setNodes((prev) =>
        prev.filter((n) => n.data.timestep === timestep)
      );
      setEdges((prev) =>
        prev.filter(
          (e) =>
            prev.find(
              (n) => n.data.id === e.data.source && n.data.timestep === timestep
            ) &&
            prev.find(
              (n) => n.data.id === e.data.target && n.data.timestep === timestep
            )
        )
      );
    }
  }, [timestep]);

  const loadExpand = useCallback(
    async (nodeId: number, depth = 2) => {
      setMode("loading");
      setError(null);
      try {
        const data = await api.graph.expand(nodeId, depth, 500);
        setNodes(data.nodes);
        setEdges(data.edges);
        setHighlightNodeIds(new Set());
        setHighlightEdgeKeys(new Set());
        setTraceInfo(null);
        // Auto-select center
        const info = await api.graph.node(nodeId);
        setSelectedNode(info);
        setMode("idle");
      } catch (e: unknown) {
        setError((e as Error).message);
        setMode("idle");
      }
    },
    []
  );

  const runTrace = useCallback(
    async (direction: "downstream" | "upstream") => {
      if (!selectedNode) return;
      setMode("tracing");
      setError(null);
      try {
        const result = await api.graph.trace(
          selectedNode.node_id,
          direction,
          10
        );
        const cy = result.cytoscape;
        setNodes(cy.nodes);
        setEdges(cy.edges);
        // Highlight trace path
        const pathNodes = new Set(result.path.map(String));
        const edgeSet = new Set<string>();
        for (let i = 0; i < result.path.length - 1; i++) {
          edgeSet.add(`${result.path[i]}→${result.path[i + 1]}`);
        }
        setHighlightNodeIds(pathNodes);
        setHighlightEdgeKeys(edgeSet);
        setTraceInfo({
          direction,
          hopCount: result.path.length - 1,
        });
        setMode("idle");
      } catch (e: unknown) {
        setError((e as Error).message);
        setMode("idle");
      }
    },
    [selectedNode]
  );

  const handleNodeClick = useCallback(async (node: CytoscapeNode) => {
    try {
      const info = await api.graph.node(Number(node.data.id));
      setSelectedNode(info);
    } catch {
      setSelectedNode({
        node_id: Number(node.data.id),
        attributes: node.data,
        in_degree: 0,
        out_degree: 0,
        degree: 0,
      });
    }
  }, []);

  const handleSearch = () => {
    const id = parseInt(searchId, 10);
    if (!isNaN(id)) {
      loadExpand(id, 2);
    }
  };

  const getNodeColor = (n: CytoscapeNode) => {
    if (highlightNodeIds.has(n.data.id)) return "#fbbf24";
    const cls = String(n.data.class ?? "3");
    return NODE_COLORS[cls] ?? "#6b7280";
  };

  const getEdgeColor = (e: CytoscapeEdge) => {
    const key = `${e.data.source}→${e.data.target}`;
    if (highlightEdgeKeys.has(key)) return "#fbbf24";
    return "rgba(255,255,255,0.1)";
  };

  return (
    <div className="flex h-full">
      {/* Graph canvas — 70% */}
      <div className="relative flex-1 bg-[var(--bg-primary)]">
        {error && (
          <div className="absolute top-4 left-4 z-10 bg-red-900/80 text-red-200 text-xs px-3 py-2 rounded-lg max-w-sm">
            {error}
          </div>
        )}

        {traceInfo && (
          <div className="absolute top-4 left-4 z-10 bg-yellow-900/80 text-yellow-200 text-xs px-3 py-2 rounded-lg">
            Trace: {traceInfo.direction} — {traceInfo.hopCount} hops,{" "}
            {highlightNodeIds.size} nodes
          </div>
        )}

        {mode === "loading" && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg-primary)]/80 z-20">
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-[var(--text-secondary)]">
                Loading subgraph…
              </span>
            </div>
          </div>
        )}

        <ForceGraph2D
          ref={fgRef}
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
          nodeLabel="id"
          nodeRelSize={4}
          linkWidth={0.5}
          onNodeClick={handleNodeClick}
          backgroundColor="var(--bg-primary)"
          width={"100%"}
          height={"100%"}
        />

        {/* Search bar */}
        <div className="absolute top-4 right-4 z-10 flex gap-1">
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

        {/* Controls */}
        <div className="absolute bottom-4 left-4 z-10 flex gap-1">
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
              selectedNode &&
              loadExpand(selectedNode.node_id, 2)
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
            }}
            className="px-2 py-1 text-xs bg-[var(--bg-panel)] border border-[var(--border-color)] hover:bg-[var(--border-color)] rounded-lg"
          >
            Reset
          </button>
        </div>

        {/* Legend */}
        <div className="absolute bottom-4 right-4 z-10 flex gap-2 text-[10px] text-[var(--text-secondary)]">
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

      {/* Inspector sidebar — 30% */}
      <div className="w-[30%] min-w-[300px]">
        <NodeInspector
          node={selectedNode}
          onTraceDown={() => runTrace("downstream")}
          onTraceUp={() => runTrace("upstream")}
          onExpand={() => selectedNode && loadExpand(selectedNode.node_id, 2)}
        />
      </div>
    </div>
  );
}
