/**
 * Resolve API base URL for the browser.
 * Prefer NEXT_PUBLIC_API_URL; otherwise use the same hostname the page
 * was loaded on (so LAN IP / hostname access still reaches the API).
 *
 * Always returns a full URL with scheme, e.g. http://192.168.101.144:8000
 * (never "http//..." or protocol-relative "//...").
 */
function getApiBase(): string {
  let base = process.env.NEXT_PUBLIC_API_URL?.trim() || "";
  if (!base && typeof window !== "undefined") {
    base = `http://${window.location.hostname || "localhost"}:8000`;
  }
  if (!base) {
    base = "http://localhost:8000";
  }
  base = base
    .replace(/^(https?):\/(?!\/)/, "$1://")
    .replace(/^(https?)\/\//, "$1://");
  if (!/^https?:\/\//i.test(base)) {
    base = `http://${base}`;
  }
  return base.replace(/\/$/, "");
}

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
    total_BTC?: number;
    fees?: number;
    size?: number;
    num_input_addresses?: number;
    num_output_addresses?: number;
    in_txs_degree?: number;
    out_txs_degree?: number;
    in_BTC_total?: number;
    out_BTC_total?: number;
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

export interface GraphSubgraph {
  nodes: CytoscapeNode[];
  edges: CytoscapeEdge[];
}

export interface TraceResult {
  nodes: number[];
  edges: [number, number][];
  hops: Record<string, number>;
  path: number[];
  cytoscape: GraphSubgraph;
}

export interface NodeAttributes {
  txId?: number;
  class?: number;
  class_label?: string;
  class_color?: string;
  timestep?: number;
  total_BTC?: number;
  fees?: number;
  size?: number;
  num_input_addresses?: number;
  num_output_addresses?: number;
  in_txs_degree?: number;
  out_txs_degree?: number;
  in_BTC_total?: number;
  out_BTC_total?: number;
  [key: string]: unknown;
}

export interface AccountParty {
  address: string;
  class_label: string;
  num_txs_as_sender?: number;
  "num_txs_as receiver"?: number;
  total_txs?: number;
  lifetime_in_blocks?: number;
  first_block_appeared_in?: number;
  last_block_appeared_in?: number;
  num_timesteps_appeared_in?: number;
  transacted_w_address_total?: number;
  [key: string]: unknown;
}

export interface AccountsPayload {
  senders: AccountParty[];
  receivers: AccountParty[];
  sender_count?: number;
  receiver_count?: number;
  profiles?: {
    by_address?: Record<string, AccountParty>;
    senders?: AccountParty[];
    receivers?: AccountParty[];
  };
  warnings?: string[];
}

export interface NodeInfo {
  node_id: number;
  attributes: NodeAttributes;
  in_degree: number;
  out_degree: number;
  degree: number;
  is_fan_out?: boolean;
  is_fan_in?: boolean;
  accounts?: AccountsPayload;
}

export interface AttributeDef {
  field: string;
  display: string;
  type: "int" | "float" | "str";
  precision?: number;
  source?: "graph" | "db";
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
  description: string;
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

// --- Hybrid graph types ---

export interface HybridNode {
  data: {
    id: string;
    kind: "transaction" | "wallet";
    address?: string;
    txId?: number;
    class?: number;
    class_label?: string;
    class_color?: string;
    timestep?: number;
    total_BTC?: number;
    fees?: number;
    size?: number;
    num_input_addresses?: number;
    num_output_addresses?: number;
    [key: string]: unknown;
  };
}

export interface HybridEdge {
  data: {
    id: string;
    source: string;
    target: string;
    role?: "input" | "output";
  };
}

export interface HybridGraphResult {
  seed_tx: number;
  nodes: HybridNode[];
  edges: HybridEdge[];
  meta: {
    sender_count: number;
    receiver_count: number;
    wallet_count: number;
    tx_count: number;
    truncated: boolean;
  };
}

export interface WalletProfile {
  address: string;
  class: number;
  class_label: string;
  class_color: string;
  [key: string]: unknown;
}

// --- Fetch helpers ---

async function get<T>(path: string): Promise<T> {
  const url = `${getApiBase()}${path}`;
  let res: Response;
  try {
    res = await fetch(url);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new Error(
      `Network error calling ${url}: ${msg}. ` +
        `Is the API running on port 8000? (uvicorn api.main:app --port 8000 --host 0.0.0.0)`,
    );
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status} on ${path}: ${text}`);
  }
  return res.json();
}

/** Merge two Cytoscape subgraphs by node/edge id (accumulate expand). */
export function mergeSubgraphs(a: GraphSubgraph, b: GraphSubgraph): GraphSubgraph {
  const nodeMap = new Map<string, CytoscapeNode>();
  for (const n of a.nodes) nodeMap.set(String(n.data.id), n);
  for (const n of b.nodes) nodeMap.set(String(n.data.id), n);

  const edgeMap = new Map<string, CytoscapeEdge>();
  const edgeKey = (e: CytoscapeEdge) =>
    `${e.data.source}\0${e.data.target}`;
  for (const e of a.edges) edgeMap.set(edgeKey(e), e);
  for (const e of b.edges) edgeMap.set(edgeKey(e), e);

  return {
    nodes: Array.from(nodeMap.values()),
    edges: Array.from(edgeMap.values()),
  };
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
      get<GraphSubgraph>(
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
    hybrid: (
      nodeId: number,
      walletDepth = 0,
      maxWallets = 50,
      maxTxs = 100
    ) =>
      get<HybridGraphResult>(
        `/graph/hybrid?node_id=${nodeId}&wallet_depth=${walletDepth}&max_wallets=${maxWallets}&max_txs=${maxTxs}`
      ),
    wallet: (address: string) => get<WalletProfile>(`/graph/wallet/${address}`),
  },
  stories: {
    list: () => get<StorySummary[]>("/stories"),
    get: (storyId: string) => get<StoryDetail>(`/stories/${storyId}`),
  },
};
