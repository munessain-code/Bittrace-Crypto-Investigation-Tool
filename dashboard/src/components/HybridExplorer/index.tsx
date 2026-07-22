"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import {
  api,
  HybridNode,
  HybridEdge,
  HybridGraphResult,
  WalletProfile,
} from "@/lib/graph-api";

// ── Constants ──────────────────────────────────────────────────────────────

const TX_COLORS: Record<string, string> = {
  "1": "#ef4444",
  "2": "#22c55e",
  "3": "#6b7280",
};

const CLASS_LABELS: Record<string, string> = {
  "1": "illicit",
  "2": "licit",
  "3": "unknown",
};

const WALLET_COLORS: Record<string, string> = {
  "1": "#fca5a5",
  "2": "#86efac",
  "3": "#9ca3af",
};

// ── Types ──────────────────────────────────────────────────────────────────

type Mode = "idle" | "loading";

interface ForceNodeData {
  id: string;
  kind: "transaction" | "wallet";
  class?: number;
  class_label?: string;
  class_color?: string;
  address?: string;
  txId?: number;
  timestep?: number;
  total_BTC?: number;
  fees?: number;
  size?: number;
  num_input_addresses?: number;
  num_output_addresses?: number;
  val?: number;
  [key: string]: unknown;
}

interface ForceLinkData {
  source: string;
  target: string;
  role?: "input" | "output";
}

// ── Helpers ────────────────────────────────────────────────────────────────

function buildTooltip(node: ForceNodeData): string {
  const lines: string[] = [];

  if (node.kind === "transaction") {
    lines.push(`<b>TX ${node.txId ?? node.id}</b>`);
    const cls = String(node.class ?? "3");
    lines.push(
      `<span style="color:${TX_COLORS[cls] || "#6b7280"}">${CLASS_LABELS[cls] ?? "unknown"}</span>`
    );
    if (node.timestep != null) lines.push(`Timestep: t=${node.timestep}`);
    if (node.total_BTC != null)
      lines.push(`Total BTC: ${(node.total_BTC as number).toFixed(4)}`);
    if (node.fees != null)
      lines.push(`Fees: ${(node.fees as number).toFixed(6)}`);
  } else {
    lines.push(`<b>Wallet</b>`);
    if (node.address) {
      const addr = node.address as string;
      const short =
        addr.length > 16
          ? `${addr.slice(0, 8)}…${addr.slice(-6)}`
          : addr;
      lines.push(`<span class="font-mono" style="font-size:10px">${short}</span>`);
    }
    const cls = String(node.class ?? "3");
    lines.push(
      `<span style="color:${WALLET_COLORS[cls] || "#9ca3af"}">${CLASS_LABELS[cls] ?? "unknown"}</span>`
    );
  }

  return lines.join("<br/>");
}

function calcVal(node: ForceNodeData): number {
  if (node.kind === "wallet") {
    if (node.class === 1) return 4;
    if (node.class === 2) return 3;
    return 3;
  }
  if (node.total_BTC && typeof node.total_BTC === "number") {
    return Math.max(3, Math.min(12, node.total_BTC * 2));
  }
  return 4;
}

// ── Component ──────────────────────────────────────────────────────────────

export function HybridExplorer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });
  const [rawResult, setRawResult] = useState<HybridGraphResult | null>(null);
  const [selectedNode, setSelectedNode] = useState<ForceNodeData | null>(null);
  const [selectedWalletProfile, setSelectedWalletProfile] =
    useState<WalletProfile | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [error, setError] = useState<string | null>(null);
  const [searchId, setSearchId] = useState("");
  const [walletDepth, setWalletDepth] = useState(0);
  const [maxWallets, setMaxWallets] = useState(50);
  const [maxTxs, setMaxTxs] = useState(100);

  // ── Resize observer ──────────────────────────────────────────────────

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      const w = Math.max(0, Math.floor(el.clientWidth));
      const h = Math.max(0, Math.floor(el.clientHeight));
      setDims((prev) =>
        prev.width === w && prev.height === h ? prev : { width: w, height: h }
      );
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ── Data loading ─────────────────────────────────────────────────────

  const loadHybrid = useCallback(
    async (txId: number) => {
      setMode("loading");
      setError(null);
      setSelectedWalletProfile(null);
      try {
        const result = await api.graph.hybrid(
          txId,
          walletDepth,
          maxWallets,
          maxTxs
        );
        setRawResult(result);
        setMode("idle");
      } catch (e: unknown) {
        setError((e as Error).message);
        setMode("idle");
      }
    },
    [walletDepth, maxWallets, maxTxs]
  );

  useEffect(() => {
    loadHybrid(10000476);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Build force graph data ───────────────────────────────────────────

  const graphData = rawResult
    ? {
        nodes: rawResult.nodes.map((n) => {
          const node = n.data as ForceNodeData;
          node.val = calcVal(node);
          return node;
        }),
        links: rawResult.edges.map((e) => ({
          source: e.data.source as string,
          target: e.data.target as string,
          role: e.data.role as "input" | "output" | undefined,
        })),
      }
    : { nodes: [] as ForceNodeData[], links: [] as ForceLinkData[] };

  // ── Styling ──────────────────────────────────────────────────────────

  const getNodeColor = (node: ForceNodeData) => {
    const cls = String(node.class ?? "3");
    if (node.kind === "wallet") {
      return WALLET_COLORS[cls] || WALLET_COLORS["3"];
    }
    return TX_COLORS[cls] || TX_COLORS["3"];
  };

  const getNodeStroke = (node: ForceNodeData) => {
    return node.kind === "wallet" ? "#ffffff44" : "transparent";
  };

  const getNodeStrokeWidth = (node: ForceNodeData) => {
    return node.kind === "wallet" ? 1.5 : 0;
  };

  const getLinkColor = (link: ForceLinkData) => {
    if (link.role === "input") return "rgba(74, 222, 128, 0.35)";
    if (link.role === "output") return "rgba(96, 165, 250, 0.35)";
    return "rgba(255,255,255,0.1)";
  };

  const getLinkWidth = (_link: ForceLinkData) => 1.2;

  // ── Event handlers ───────────────────────────────────────────────────

  const handleNodeClick = useCallback(async (node: ForceNodeData) => {
    setSelectedNode(node);
    setSelectedWalletProfile(null);

    if (node.kind === "wallet" && node.address) {
      try {
        const profile = await api.graph.wallet(node.address as string);
        setSelectedWalletProfile(profile);
      } catch {
        // Show what we have
      }
    }
  }, []);

  const handleSearch = () => {
    const id = parseInt(searchId, 10);
    if (!isNaN(id)) {
      loadHybrid(id);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────

  return (
    <div className="flex h-full min-h-0 w-full overflow-hidden">
      {/* Graph canvas */}
      <div
        ref={containerRef}
        className="relative flex-1 min-w-0 min-h-0 overflow-hidden bg-[var(--bg-primary)]"
      >
        {dims.width > 0 && dims.height > 0 && (
          <ForceGraph2D
            graphData={graphData}
            nodeColor={getNodeColor}
            nodeStrokeColor={getNodeStroke}
            nodeStrokeWidth={getNodeStrokeWidth}
            nodeRelSize={1}
            nodeCanvasObject={(node, ctx) => {
              const data = node as ForceNodeData;
              const id = String(data.id);
              if (id.startsWith("tx:")) {
                const val = (data.val as number) || 6;
                const w = val * 2;
                const h = val * 1.4;
                const cls = String(data.class ?? "3");
                ctx.fillStyle = TX_COLORS[cls] || TX_COLORS["3"];
                ctx.shadowBlur = 6;
                ctx.shadowColor = "rgba(0,0,0,0.4)";
                ctx.fillRect(-w / 2, -h / 2, w, h);
                ctx.shadowBlur = 0;
                ctx.fillStyle = "#fff";
                ctx.font = "8px sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                const label = id.slice(3);
                ctx.fillText(label, 0, 0);
              }
            }}
            linkColor={getLinkColor}
            linkWidth={getLinkWidth}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            linkDirectionalParticles={0}
            nodeLabel={buildTooltip}
            onNodeClick={handleNodeClick}
            backgroundColor="var(--bg-primary)"
            width={dims.width}
            height={dims.height}
            d3AlphaDecay={0.06}
          />
        )}

        {/* ── Overlays ──────────────────────────────────────────────── */}
        <div className="absolute inset-0 pointer-events-none z-10 flex flex-col justify-between p-3 sm:p-4 gap-2 overflow-hidden">
          {/* Top row: error + search */}
          <div className="flex justify-between items-start gap-2 shrink-0">
            <div className="flex flex-col gap-1 max-w-sm">
              {error && (
                <div className="bg-red-900/80 text-red-200 text-xs px-3 py-2 rounded-lg pointer-events-auto">
                  {error}
                </div>
              )}
              {rawResult && (
                <div className="bg-[var(--bg-panel)]/80 text-[var(--text-secondary)] text-xs px-3 py-1.5 rounded-lg pointer-events-auto">
                  Seed TX {rawResult.seed_tx} · {rawResult.meta.tx_count} txs ·{" "}
                  {rawResult.meta.wallet_count} wallets
                </div>
              )}
            </div>
            <div className="flex gap-1 pointer-events-auto items-center">
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

          {/* Bottom row: controls */}
          <div className="flex flex-col gap-2 shrink-0">
            <div className="flex flex-wrap items-center gap-2 pointer-events-auto bg-[var(--bg-panel)]/90 border border-[var(--border-color)] rounded-lg px-2 py-1.5 text-[10px] text-[var(--text-secondary)]">
              <span className="font-semibold text-white/80">Wallet Depth</span>
              <label className="flex items-center gap-1">
                depth
                <select
                  value={walletDepth}
                  onChange={(e) => {
                    setWalletDepth(Number(e.target.value));
                  }}
                  className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-1 py-0.5 text-white"
                >
                  <option value={0}>0 (parties only)</option>
                  <option value={1}>1 (neighbors)</option>
                </select>
              </label>
              <label className="flex items-center gap-1">
                wallets
                <select
                  value={maxWallets}
                  onChange={(e) => setMaxWallets(Number(e.target.value))}
                  className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-1 py-0.5 text-white"
                >
                  {[10, 25, 50, 100, 200].map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-1">
                txs
                <select
                  value={maxTxs}
                  onChange={(e) => setMaxTxs(Number(e.target.value))}
                  className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-1 py-0.5 text-white"
                >
                  {[25, 50, 100, 200, 500].map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </label>
              <button
                onClick={() => { if (rawResult) loadHybrid(rawResult.seed_tx); }}
                className="px-2 py-0.5 text-xs bg-blue-600/80 hover:bg-blue-500 rounded-lg"
              >
                Apply
              </button>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-2 text-[10px] text-[var(--text-secondary)] bg-[var(--bg-primary)]/70 px-2 py-1 rounded pointer-events-auto">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500" /> Illicit TX
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500" /> Licit TX
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-gray-500" /> Unknown TX
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full border border-white/40 bg-red-300" />{" "}
                Illicit Wallet
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full border border-white/40 bg-green-300" />{" "}
                Licit Wallet
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-0.5 bg-green-400/60" /> Input
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-0.5 bg-blue-400/60" /> Output
              </span>
            </div>
          </div>
        </div>

        {/* Loading spinner */}
        {mode === "loading" && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg-primary)]/80 z-30">
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-[var(--text-secondary)]">
                Loading hybrid graph…
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── Side panel ──────────────────────────────────────────────── */}
      <div className="w-[min(30%,360px)] min-w-[240px] max-w-[360px] shrink-0 min-h-0 overflow-hidden border-l border-[var(--border-color)]">
        <NodeSidePanel
          node={selectedNode}
          walletProfile={selectedWalletProfile}
          onNavigate={loadHybrid}
        />
      </div>
    </div>
  );
}

// ── Side panel ────────────────────────────────────────────────────────────

function NodeSidePanel({
  node,
  walletProfile,
  onNavigate,
}: {
  node: ForceNodeData | null;
  walletProfile: WalletProfile | null;
  onNavigate: (txId: number) => void;
}) {
  if (!node) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--text-secondary)] text-sm bg-[var(--bg-panel)]">
        Select a node to inspect
      </div>
    );
  }

  const clsLabel = (node.class_label as string) ?? "unknown";
  const clsColor = (node.class_color as string) ?? "#6b7280";

  return (
    <div className="flex flex-col h-full bg-[var(--bg-panel)] border-l border-[var(--border-color)] overflow-auto">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)] space-y-2">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full shrink-0"
            style={{ backgroundColor: clsColor }}
          />
          <h2 className="font-mono text-sm">
            {node.kind === "transaction" ? `TX ${node.txId ?? node.id}` : "Wallet"}
          </h2>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 uppercase tracking-wide">
            {node.kind}
          </span>
        </div>
        <span
          className="inline-block px-2 py-0.5 text-xs rounded-full border font-medium capitalize bg-opacity-20"
          style={{
            backgroundColor: `${clsColor}33`,
            borderColor: `${clsColor}66`,
            color: clsColor,
          }}
        >
          {clsLabel}
        </span>
      </div>

      {/* TX details */}
      {node.kind === "transaction" && (
        <div className="p-4 border-t border-[var(--border-color)] space-y-3">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Transaction Details
          </h3>
          <div className="space-y-2">
            {node.timestep != null && (
              <AttrRow label="Timestep" value={`t=${node.timestep}`} />
            )}
            {node.total_BTC != null && (
              <AttrRow
                label="Total BTC"
                value={(node.total_BTC as number).toFixed(6)}
              />
            )}
            {node.fees != null && (
              <AttrRow
                label="Fees"
                value={(node.fees as number).toFixed(8)}
              />
            )}
            {node.size != null && (
              <AttrRow
                label="Size"
                value={`${(node.size as number).toFixed(0)} bytes`}
              />
            )}
            {node.num_input_addresses != null && (
              <AttrRow
                label="Input Addresses"
                value={String(node.num_input_addresses)}
              />
            )}
            {node.num_output_addresses != null && (
              <AttrRow
                label="Output Addresses"
                value={String(node.num_output_addresses)}
              />
            )}
          </div>
        </div>
      )}

      {/* Wallet address */}
      {node.kind === "wallet" && node.address && (
        <div className="p-4 border-t border-[var(--border-color)] space-y-3">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Address
          </h3>
          <div className="font-mono text-xs text-white break-all bg-[var(--bg-primary)] rounded px-2 py-1.5">
            {(node.address as string)}
          </div>
        </div>
      )}

      {/* Wallet profile from API */}
      {walletProfile && (
        <div className="p-4 border-t border-[var(--border-color)] space-y-3">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Wallet Profile
          </h3>
          <div className="space-y-2">
            {Object.entries(walletProfile)
              .filter(
                ([k]) =>
                  !["address", "class", "class_label", "class_color"].includes(
                    k
                  )
              )
              .map(([k, v]) => (
                <AttrRow
                  key={k}
                  label={formatLabel(k)}
                  value={
                    typeof v === "number" ? v.toFixed(2) : String(v ?? "—")
                  }
                />
              ))}
          </div>
        </div>
      )}

      {/* Navigate button for TX nodes */}
      {node.kind === "transaction" && node.txId && (
        <div className="p-4 border-t border-[var(--border-color)]">
          <button
            onClick={() => onNavigate(node.txId as number)}
            className="w-full px-3 py-2 text-xs bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors text-center"
          >
            ↻ Reload as Seed TX
          </button>
        </div>
      )}
    </div>
  );
}

function AttrRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs gap-2">
      <span className="text-[var(--text-secondary)] shrink-0">{label}</span>
      <span className="font-mono text-right break-all">{value}</span>
    </div>
  );
}

function formatLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
