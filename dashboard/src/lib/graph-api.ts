const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Types ---

export interface GraphOverview {
  total_nodes: number;
  total_edges: number;
  class_counts: Record<string, number>;
  class_labels: Record<string, string>;
  timestep_counts: Record<string, number>;
  illicit_per_timestep: Record<string, number>;
  class_flow: Record<string, number>;
  density: number;
}

export interface CytoscapeNode {
  data: {
    id: string;
    class?: number;
    class_label?: string;
    class_color?: string;
    timestep?: number;
    step?: number;
    [key: string]: unknown;
  };
}

export interface CytoscapeEdge {
  data: {
    source: string;
    target: string;
    step?: number;
  };
}

export interface TraceResult {
  nodes: number[];
  edges: [number, number][];
  hops: Record<string, number>;
  path: number[];
  cytoscape: { nodes: CytoscapeNode[]; edges: CytoscapeEdge[] };
}

export interface NodeInfo {
  node_id: number;
  attributes: Record<string, unknown>;
  in_degree: number;
  out_degree: number;
  degree: number;
}

export interface StorySummary {
  id: string;
  title: string;
  difficulty: string;
  pattern: string;
  seed_node_id: number;
  step_count: number;
  narrative_preview: string;
}

export interface StoryStep {
  step_num: number;
  title: string;
  narrative: string;
  trace_direction: "downstream" | "upstream";
  highlight_nodes: number[];
  highlight_edges: [number, number][];
}

export interface StoryDetail {
  id: string;
  title: string;
  difficulty: string;
  pattern: string;
  seed_node_id: number;
  narrative: string;
  steps: StoryStep[];
}

// --- Fetch helpers ---

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status} on ${path}: ${text}`);
  }
  return res.json();
}

// --- API ---

export const api = {
  graph: {
    overview: () => get<GraphOverview>("/graph/overview"),
    subgraph: (caseId: string) =>
      get<{ story?: StoryDetail; nodes: CytoscapeNode[]; edges: CytoscapeEdge[] }>(
        `/graph/subgraph/${caseId}`
      ),
    expand: (nodeId: number, depth = 1, maxNodes = 500) =>
      get<{ nodes: CytoscapeNode[]; edges: CytoscapeEdge[] }>(
        `/graph/expand?node_id=${nodeId}&depth=${depth}&max_nodes=${maxNodes}`
      ),
    trace: (
      nodeId: number,
      direction: "downstream" | "upstream" = "downstream",
      maxHops = 10
    ) =>
      get<TraceResult>(
        `/graph/trace?node_id=${nodeId}&direction=${direction}&max_hops=${maxHops}`
      ),
    node: (nodeId: number) => get<NodeInfo>(`/graph/node/${nodeId}`),
  },
  stories: {
    list: () => get<StorySummary[]>("/stories"),
    get: (storyId: string) => get<StoryDetail>(`/stories/${storyId}`),
  },
};
