import { AnimatePresence, motion } from "framer-motion";
import { Info, X } from "lucide-react";
import { useState } from "react";

// Metric NAMES only, deliberately no weights/percentages/thresholds - per
// explicit decision, this is a partial reversal of gate_config.py's own
// documented constraint ("metric definitions and weights never reach the
// frontend", tracing to the original PRD's "no weights or metric
// definitions in the payload" output-layer spec). Naming which metrics
// drive each score without publishing the exact formula. Grounded directly
// in the scoring modules, not invented:
//   - Corridor: scoring/corridor.py + gate_config.py (5 gates, must all
//     pass to be eligible, seed/placeholder data for every city right now)
//   - Society: scoring/society_fit.py (4 weighted metrics, real/live data)
//   - Broker: scoring/broker_list.py (1 metric, real/live data)
//   - NRI: scoring/validated_signals.py (2 rule-based detections, not a
//     weighted score at all - shown distinctly for that reason)
const METRIC_GROUPS: { label: string; note?: string; items: string[] }[] = [
  {
    label: "Corridor",
    items: ["Price-band fit", "Demand-hub proximity", "Clean title / RERA", "Comp density", "Resale velocity"],
  },
  {
    label: "Society",
    items: ["Supply depth", "Resale velocity", "Price consistency", "Rating"],
  },
  {
    label: "Broker",
    items: ["Listing activity"],
  },
  {
    label: "NRI signals",
    note: "rule-based",
    items: ["Multiple properties, one owner", "Never-occupied listing language"],
  },
];

// Collapsed by default, same interaction language as ExplainPanel (a
// labeled toggle, not a tiny icon-only affordance, so what it is stays
// obvious even closed) - an always-open panel here covered the map's own
// city markers at mobile widths (390px), which is exactly the "interferes
// with the UI" outcome ruled out explicitly. Top-left per instruction;
// content and copy unchanged from the always-open version, just gated
// behind one click/tap.
export function SelectionMetrics() {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed left-6 top-20 z-30 sm:left-10 sm:top-24">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Hide selection metrics" : "Show selection metrics"}
        aria-expanded={open}
        className={`flex items-center gap-1.5 rounded-sm border px-2.5 py-1.5 text-xs font-medium backdrop-blur-md transition-colors duration-200 ${
          open ? "border-lime-400/50 bg-black/65 text-lime-400" : "border-white/20 bg-black/50 text-white/70 hover:text-white/90"
        }`}
      >
        <Info size={13} />
        Selection Metrics
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="mt-2 w-72 max-w-[calc(100vw-3rem)] rounded-sm border border-white/15 bg-black/70 p-4 backdrop-blur-md"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-[10px] leading-relaxed text-white/40">
                What the AI weighs when ranking corridors, societies, brokers and NRI signals.
              </p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close selection metrics"
                className="shrink-0 text-white/40 hover:text-white"
              >
                <X size={14} />
              </button>
            </div>

            <div className="mt-3 space-y-2.5">
              {METRIC_GROUPS.map((group) => (
                <div key={group.label}>
                  <p className="text-[10px] font-medium uppercase tracking-wide text-lime-400/80">
                    {group.label}
                    {group.note && <span className="ml-1 normal-case text-white/30">({group.note})</span>}
                  </p>
                  <p className="mt-0.5 text-[11px] leading-relaxed text-white/70">{group.items.join(" · ")}</p>
                </div>
              ))}
            </div>

            <p className="mt-3 border-t border-white/10 pt-2.5 text-[10px] leading-relaxed text-white/35">
              <span className="text-white/50">Note:</span> These are the current decision-making metrics. They
              are fully configurable and can be modified based on a company&apos;s priorities or business
              strategy. Once the metrics change, the AI agent automatically adjusts its recommendations
              accordingly. In other words, the metrics are the &quot;brain&quot; behind the recommendation
              engine.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
