"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph3D from "react-force-graph-3d";
import { api, CytoscapeNode, CytoscapeEdge, NodeInfo, NodeAttributes } from "@/lib/graph-api";
import { NodeInspector } from "@/components/NodeInspector";

// Shared class colors
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
type ForceNode = { id: string; class?: number; timestep?: number } & Record<string, unknown>;
type ForceLink = { source: string; target: string };

// Build a compact hover tooltip from HOVER_ATTRIBUTES
function buildTooltip(node: ForceNode): string {
  const lines: string[] = [];
  lines.push(`<b>TX ${node.id}</b>`);
  const cls = String(node.class ?? "3");
  lines.push(`Class: <span style="color:${NODE_COLORS[cls] || '#6b7280'}">${CLASS_LABELS[cls] ?? "unknown"}</span>`);
  if (node.timestep !== undefined && node.timestep !== null) lines.push(`Timestep: t=${node.timestep}`);
  if (node.total_BTC !== undefined && node.total_BTC !== null)
    lines.push(`Total BTC: ${(node.total_BTC as number).toFixed(4)}`);
  if (node.fees !== undefined && node.fees !== null)
    lines.push(`Fees: ${(node.fees as number).toFixed(6)}`);
  if (node.num_input_addresses !== undefined) lines.push(`Inputs: ${node.num_input_addresses}`);
  if (node.num_output_addresses !== undefined) lines.push(`Outputs: ${node.num_output_addresses}`);
  if (node.in_txs_degree !== undefined) lines.push(`In-degree: ${node.in_txs_degree}`);
  if (node.out_txs_degree !== undefined) lines.push(`Out-degree: ${node.out_txs_degree}`);
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

export function GraphExplorer3D({
  timestep,
  selectedClass,
}: {
  timestep: number | null;
  selectedClass: string | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
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
  } | null>(null);
  const [highlightNodeIds, setHighlightNodeIds] = useState<Set<string>>(new Set());
  const [highlightEdgeKeys, setHighlightEdgeKeys] = useState<Set<string>>(new Set());
  const [searchId, setSearchId] = useState("");
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

  const loadExpand = useCallback(
    async (nodeId: number, depth = 2) => {
      setMode("loading");
      setError(null);
      try {
        const data = await api.graph.expand(nodeId, depth, 500);
        setFullNodes(data.nodes);
        setFullEdges(data.edges);
        setHighlightNodeIds(new Set());
        setHighlightEdgeKeys(new Set());
        setTraceInfo(null);
        const info = await api.graph.node(nodeId);
        setSelectedNode(info);
        setMode("idle");
      } catch (e: unknown) {
        setError((e as Error).message);
        setMode("idle");
      }
    },
    [],
  );

  useEffect(() => {
    loadExpand(10000476, 2);
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
        setFullNodes(cy.nodes);
        setFullEdges(cy.edges);
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
    [selectedNode],
  );

  const handleNodeClick = useCallback(async (node: ForceNode) => {
    try {
      const info = await api.graph.node(Number(node.id));
      setSelectedNode(info);
    } catch {
      setSelectedNode({
        node_id: Number(node.id),
        attributes: node as NodeAttributes,
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

  const getNodeColor = (n: ForceNode) => {
    if (highlightNodeIds.has(n.id)) return "#fbbf24";
    const cls = String(n.class ?? "3");
    return NODE_COLORS[cls] ?? "#6b7280";
  };

  const getEdgeColor = (e: ForceLink) => {
    const key = `${e.source}→${e.target}`;
    if (highlightEdgeKeys.has(key)) return "#fbbf24";
    return "rgba(255,255,255,0.1)";
  };

  return (
    <div className="flex h-full">
      <div ref={containerRef} className="relative flex-1 bg-[var(--bg-primary)]">
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

        <ForceGraph3D
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
          nodeLabel={(n: ForceNode) => buildTooltip(n)}
          nodeVal={4}
          linkWidth={0.5}
          onNodeClick={handleNodeClick}
          backgroundColor="var(--bg-primary)"
          width={dims.width}
          height={dims.height}
          showNavInfo={false}
        />

        {/* Search */}
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

        {/* Trace controls */}
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

      {/* Node Inspector sidebar */}
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
