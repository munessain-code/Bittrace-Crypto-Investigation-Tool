"use client";

import { NodeInfo } from "@/lib/graph-api";

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

// CLICK_ATTRIBUTES display mapping
const ATTR_DISPLAY: Record<string, { label: string; format?: (v: unknown) => string }> = {
  txId: { label: "TX ID" },
  class_label: { label: "Class" },
  class: { label: "Class ID" },
  timestep: { label: "Timestep", format: (v) => `t=${v}` },
  total_BTC: { label: "Total BTC", format: (v) => (typeof v === "number" ? v.toFixed(6) : String(v)) },
  fees: { label: "Fees", format: (v) => (typeof v === "number" ? v.toFixed(8) : String(v)) },
  size: { label: "TX Size (bytes)", format: (v) => (typeof v === "number" ? v.toFixed(1) : String(v)) },
  num_input_addresses: { label: "Inputs" },
  num_output_addresses: { label: "Outputs" },
  in_BTC_total: { label: "Input BTC", format: (v) => (typeof v === "number" ? v.toFixed(6) : String(v)) },
  out_BTC_total: { label: "Output BTC", format: (v) => (typeof v === "number" ? v.toFixed(6) : String(v)) },
  in_txs_degree: { label: "Input TXs (graph)" },
  out_txs_degree: { label: "Output TXs (graph)" },
};

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

  // Build formatted attribute rows from CLICK_ATTRIBUTES
  const attrRows = Object.entries(attrs)
    .filter(([k]) => ![
      "class_label",
      "class_color",
      "in_degree",
      "out_degree",
      "degree",
      "txId",
    ].includes(k))
    .map(([k, v]) => {
      const display = ATTR_DISPLAY[k];
      return {
        label: display?.label ?? k,
        value: display?.format ? display.format(v) : String(v ?? "—"),
      };
    });

  return (
    <div className="flex flex-col h-full bg-[var(--bg-panel)] border-l border-[var(--border-color)] overflow-auto">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: clsColor }}
          />
          <h2 className="font-mono text-sm">TX {node.node_id}</h2>
        </div>
        <span
          className={`mt-2 inline-block px-2 py-0.5 text-xs rounded-full border font-medium capitalize ${
            CLASS_BGS[clsLabel] ?? CLASS_BGS.unknown
          } ${CLASS_COLORS[clsLabel] ?? "text-gray-400"}`}
        >
          {clsLabel}
        </span>
      </div>

      {/* Core attributes */}
      <div className="p-4 space-y-3">
        <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
          Attributes
        </h3>
        <div className="space-y-2">
          <AttrRow label="Degree" value={String(node.degree)} />
          <AttrRow label="In-Degree" value={String(node.in_degree)} />
          <AttrRow label="Out-Degree" value={String(node.out_degree)} />
        </div>
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
            ⊕ Expand 1-Hop
          </button>
        </div>
      </div>

      {/* Raw attributes */}
      <div className="p-4 border-t border-[var(--border-color)] flex-1">
        <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
          All Attributes
        </h3>
        <div className="max-h-40 overflow-auto text-[10px] font-mono space-y-0.5">
          {Object.entries(attrs)
            .filter(([k]) => ![
              "class_label",
              "class_color",
              "in_degree",
              "out_degree",
              "degree",
            ].includes(k))
            .map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-[var(--text-secondary)]">{k}</span>
                <span className="text-white">{String(v)}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

function AttrRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-[var(--text-secondary)]">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}
