"use client";

import { NodeInfo, AccountParty } from "@/lib/graph-api";

const CLASS_COLORS: Record<string, string> = {
  illicit: "text-red-400",
  licit: "text-green-400",
  unknown: "text-gray-400",
};

const CLASS_BGS: Record<string, string> = {
  illicit: "bg-red-500/20 border-red-500/40",
  licit: "bg-green-500/20 border-green-500/40",
  unknown: "bg-gray-500/20 border-gray-500/40",
};

/** Transaction value fields only — never show raw class integers here */
const TX_DETAIL_KEYS = [
  "timestep",
  "total_BTC",
  "fees",
  "size",
  "in_BTC_total",
  "out_BTC_total",
  "num_input_addresses",
  "num_output_addresses",
  "in_txs_degree",
  "out_txs_degree",
] as const;

const ATTR_DISPLAY: Record<string, { label: string; format?: (v: unknown) => string }> = {
  timestep: { label: "Timestep", format: (v) => `t=${v}` },
  total_BTC: {
    label: "Total BTC",
    format: (v) => (typeof v === "number" ? v.toFixed(6) : String(v)),
  },
  fees: {
    label: "Fees",
    format: (v) => (typeof v === "number" ? v.toFixed(8) : String(v)),
  },
  size: {
    label: "TX Size (bytes)",
    format: (v) => (typeof v === "number" ? v.toFixed(1) : String(v)),
  },
  num_input_addresses: { label: "Input addresses" },
  num_output_addresses: { label: "Output addresses" },
  in_BTC_total: {
    label: "Input BTC",
    format: (v) => (typeof v === "number" ? v.toFixed(6) : String(v)),
  },
  out_BTC_total: {
    label: "Output BTC",
    format: (v) => (typeof v === "number" ? v.toFixed(6) : String(v)),
  },
  in_txs_degree: { label: "Input TXs (feature)" },
  out_txs_degree: { label: "Output TXs (feature)" },
};

const PROFILE_DISPLAY: Record<string, { label: string; format?: (v: unknown) => string }> = {
  num_txs_as_sender: { label: "TXs as Sender" },
  "num_txs_as receiver": { label: "TXs as Receiver" },
  total_txs: { label: "Total TXs" },
  lifetime_in_blocks: {
    label: "Lifetime (blocks)",
    format: (v) => (typeof v === "number" ? Math.round(v).toLocaleString() : String(v)),
  },
  first_block_appeared_in: {
    label: "First Block",
    format: (v) => (typeof v === "number" ? Math.round(v).toLocaleString() : String(v)),
  },
  last_block_appeared_in: {
    label: "Last Block",
    format: (v) => (typeof v === "number" ? Math.round(v).toLocaleString() : String(v)),
  },
  num_timesteps_appeared_in: { label: "Active Timesteps" },
  transacted_w_address_total: {
    label: "Unique Counterparties",
    format: (v) => (typeof v === "number" ? Math.round(v).toLocaleString() : String(v)),
  },
};

function partyProfileFields(party: AccountParty): { label: string; value: string }[] {
  return Object.entries(party)
    .filter(([k]) => PROFILE_DISPLAY[k] != null)
    .map(([k, v]) => {
      const d = PROFILE_DISPLAY[k]!;
      return {
        label: d.label,
        value: d.format ? d.format(v) : String(v ?? "—"),
      };
    });
}

function truncateAddr(addr: string, n = 10): string {
  if (addr.length <= n * 2 + 1) return addr;
  return `${addr.slice(0, n)}…${addr.slice(-n)}`;
}

export function NodeInspector({
  node,
  onTraceDown,
  onTraceUp,
  onExpand,
}: {
  node: NodeInfo | null;
  onTraceDown: () => void;
  onTraceUp: () => void;
  onExpand: () => void;
}) {
  if (!node) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--text-secondary)] text-sm">
        Select a node to inspect
      </div>
    );
  }

  const attrs = node.attributes ?? {};
  const clsLabel = (attrs.class_label as string) ?? "unknown";
  const clsColor = (attrs.class_color as string) ?? "#6b7280";
  const fanOut = node.is_fan_out ?? node.out_degree > 1;
  const fanIn = node.is_fan_in ?? node.in_degree > 1;

  const attrRows = TX_DETAIL_KEYS.filter((k) => attrs[k] !== undefined && attrs[k] !== null)
    .map((k) => {
      const display = ATTR_DISPLAY[k];
      const v = attrs[k];
      return {
        label: display?.label ?? k,
        value: display?.format ? display.format(v) : String(v ?? "—"),
      };
    });

  const senderCount = node.accounts?.sender_count ?? node.accounts?.senders?.length ?? 0;
  const receiverCount =
    node.accounts?.receiver_count ?? node.accounts?.receivers?.length ?? 0;
  const shownSenders = node.accounts?.senders?.length ?? 0;
  const shownReceivers = node.accounts?.receivers?.length ?? 0;

  return (
    <div className="flex flex-col h-full bg-[var(--bg-panel)] border-l border-[var(--border-color)] overflow-auto">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)] space-y-2">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full shrink-0"
            style={{ backgroundColor: clsColor }}
          />
          <h2 className="font-mono text-sm">TX {node.node_id}</h2>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span
            className={`inline-block px-2 py-0.5 text-xs rounded-full border font-medium capitalize ${
              CLASS_BGS[clsLabel] ?? CLASS_BGS.unknown
            } ${CLASS_COLORS[clsLabel] ?? "text-gray-400"}`}
          >
            {clsLabel}
          </span>
          {fanOut && (
            <span
              className="inline-block px-2 py-0.5 text-xs rounded-full border border-orange-500/50 bg-orange-500/20 text-orange-300 font-medium"
              title={`This transaction has ${node.out_degree} outgoing TX edges (fan-out)`}
            >
              Fan-out ×{node.out_degree}
            </span>
          )}
          {fanIn && (
            <span
              className="inline-block px-2 py-0.5 text-xs rounded-full border border-cyan-500/50 bg-cyan-500/20 text-cyan-300 font-medium"
              title={`This transaction has ${node.in_degree} incoming TX edges (fan-in)`}
            >
              Fan-in ×{node.in_degree}
            </span>
          )}
        </div>
      </div>

      {/* Graph degrees */}
      <div className="p-4 space-y-3">
        <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
          Graph
        </h3>
        <div className="space-y-2">
          <AttrRow label="Degree" value={String(node.degree)} />
          <AttrRow label="In-Degree" value={String(node.in_degree)} />
          <AttrRow label="Out-Degree" value={String(node.out_degree)} />
        </div>
        {fanOut && (
          <p className="text-[10px] text-orange-300/90 leading-relaxed">
            Money continues to {node.out_degree} next transactions. Use{" "}
            <strong>Expand</strong> or <strong>Trace Down</strong> to follow all
            branches — not only a single peel-chain hop.
          </p>
        )}
      </div>

      {/* Transaction details */}
      {attrRows.length > 0 && (
        <div className="p-4 border-t border-[var(--border-color)] space-y-3">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Transaction Details
          </h3>
          <div className="space-y-2">
            {attrRows.map((row) => (
              <AttrRow key={row.label} label={row.label} value={row.value} />
            ))}
          </div>
        </div>
      )}

      {/* Account details */}
      {node.accounts && (
        <div className="p-4 border-t border-[var(--border-color)] space-y-4">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Account Details
          </h3>

          {node.accounts.warnings && node.accounts.warnings.length > 0 && (
            <div className="text-[10px] text-amber-300/90 bg-amber-900/20 border border-amber-500/30 rounded px-2 py-1">
              Partial account data: {node.accounts.warnings.join(", ")}
            </div>
          )}

          <PartyList
            title="Senders"
            accent="text-green-400"
            parties={node.accounts.senders}
            totalCount={senderCount}
            shownCount={shownSenders}
          />
          <PartyList
            title="Receivers"
            accent="text-blue-400"
            parties={node.accounts.receivers}
            totalCount={receiverCount}
            shownCount={shownReceivers}
          />
        </div>
      )}

      {/* Actions */}
      <div className="p-4 space-y-2 border-t border-[var(--border-color)]">
        <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
          Actions
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={onTraceDown}
            className="px-3 py-2 text-xs bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors text-center"
          >
            ▶ Trace Down
          </button>
          <button
            onClick={onTraceUp}
            className="px-3 py-2 text-xs bg-purple-600 hover:bg-purple-500 rounded-lg transition-colors text-center"
          >
            ◀ Trace Up
          </button>
          <button
            onClick={onExpand}
            className="px-3 py-2 text-xs bg-[var(--bg-primary)] hover:bg-[var(--border-color)] rounded-lg transition-colors col-span-2 text-center"
          >
            ⊕ Expand neighborhood
          </button>
        </div>
      </div>
    </div>
  );
}

function PartyList({
  title,
  accent,
  parties,
  totalCount,
  shownCount,
}: {
  title: string;
  accent: string;
  parties: AccountParty[];
  totalCount: number;
  shownCount: number;
}) {
  const more = Math.max(0, totalCount - shownCount);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className={`text-[10px] font-semibold uppercase ${accent}`}>
          {title} ({totalCount})
        </span>
        {more > 0 && (
          <span className="text-[10px] text-[var(--text-secondary)]">
            showing {shownCount}, +{more} more
          </span>
        )}
      </div>
      <div className="space-y-1">
        {parties.length === 0 && (
          <div className="text-[11px] text-[var(--text-secondary)]">None linked</div>
        )}
        {parties.map((party) => {
          const fields = partyProfileFields(party);
          return (
            <div
              key={party.address}
              className="bg-[var(--bg-primary)] rounded-lg p-2 space-y-1"
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className="font-mono text-[11px] text-white truncate"
                  title={party.address}
                >
                  {truncateAddr(party.address)}
                </span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 capitalize ${
                    CLASS_BGS[party.class_label] ?? CLASS_BGS.unknown
                  } ${CLASS_COLORS[party.class_label] ?? "text-gray-400"}`}
                >
                  {party.class_label}
                </span>
              </div>
              {fields.length > 0 && (
                <div className="grid grid-cols-2 gap-x-2 gap-y-0.5">
                  {fields.map((f) => (
                    <AttrRow
                      key={`${party.address}-${f.label}`}
                      label={f.label}
                      value={f.value}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
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
