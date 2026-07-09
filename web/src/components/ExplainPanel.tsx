import { AnimatePresence, motion } from "framer-motion";
import { Info, X } from "lucide-react";
import { useState } from "react";

interface Metric {
  label: string;
  value: string;
}

interface ExplainPanelProps {
  title: string;
  metrics: Metric[];
  note?: string;
}

// Small, low-key corner panel - a toggle button that's always visible (so
// the info is genuinely reachable, not buried), revealing real metric
// values on click rather than an always-open panel competing with the main
// content. Bottom-right; nothing else in either screen this is used on
// currently occupies that corner.
export function ExplainPanel({ title, metrics, note }: ExplainPanelProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-5 right-5 z-40">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="mb-3 w-72 rounded-sm border border-white/15 bg-black/60 p-4 text-sm backdrop-blur-md"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-xs font-medium uppercase tracking-wide text-white/60">{title}</h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close explanation"
                className="shrink-0 text-white/40 hover:text-white"
              >
                <X size={14} />
              </button>
            </div>
            <dl className="mt-3 space-y-1.5">
              {metrics.map((m) => (
                <div key={m.label} className="flex items-baseline justify-between gap-3 text-xs">
                  <dt className="text-white/45">{m.label}</dt>
                  <dd className="text-right text-white/85">{m.value}</dd>
                </div>
              ))}
            </dl>
            {note && <p className="mt-3 border-t border-white/10 pt-2 text-[10px] leading-relaxed text-white/35">{note}</p>}
          </motion.div>
        )}
      </AnimatePresence>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Hide ranking explanation" : "Show ranking explanation"}
        aria-expanded={open}
        className={`flex h-9 w-9 items-center justify-center rounded-full border backdrop-blur-md transition-colors duration-200 ${
          open ? "border-lime-400/50 bg-black/60 text-lime-400" : "border-white/20 bg-black/40 text-white/50 hover:text-white/80"
        }`}
      >
        <Info size={16} />
      </button>
    </div>
  );
}
