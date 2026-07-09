import { AnimatePresence, motion } from "framer-motion";
import { Database, ExternalLink, SearchCode, X } from "lucide-react";
import { createContext, useContext, useState, type ReactNode } from "react";

export interface SourceRow {
  label: string;
  value: string;
  href?: string;
}

export interface SourceSpec {
  title: string;
  /** Exact file this number/tile traces to - always a real path, never "the database". */
  sourceFile: string;
  /** One or two sentences: what was counted/filtered/computed, in plain words. */
  summary: string;
  rows: SourceRow[];
  /** e.g. "+42 more candidate rows not shown" when rows[] is a sample, not the full set. */
  moreCount?: number;
}

interface SourceInspectorContextValue {
  open: (spec: SourceSpec) => void;
}

const SourceInspectorContext = createContext<SourceInspectorContextValue>({ open: () => {} });

export function useSourceInspector() {
  return useContext(SourceInspectorContext).open;
}

/**
 * The "don't settle for trust us" layer: any headline number or corridor/
 * society/broker score can open this and show exactly which file it came
 * from, how it was derived, and a sample of the real underlying rows
 * (with a live detail_url where one exists). Nothing here is computed fresh -
 * every SourceSpec is built from data already loaded via DataProvider.
 */
export function SourceInspectorProvider({ children }: { children: ReactNode }) {
  const [spec, setSpec] = useState<SourceSpec | null>(null);

  return (
    <SourceInspectorContext.Provider value={{ open: setSpec }}>
      {children}
      <AnimatePresence>
        {spec && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/60"
              onClick={() => setSpec(null)}
            />
            <motion.div
              initial={{ opacity: 0, y: 16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 16, scale: 0.98 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              role="dialog"
              aria-modal="true"
              className="glass-hi fixed inset-x-4 top-1/2 z-50 mx-auto max-h-[80vh] max-w-lg -translate-y-1/2 overflow-hidden rounded-2xl sm:inset-x-auto"
            >
              <div className="flex items-start justify-between gap-4 border-b border-line p-5">
                <div>
                  <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-text-faint">
                    <SearchCode size={13} /> Source
                  </div>
                  <div className="mt-1 font-display text-lg font-medium text-text-hi">{spec.title}</div>
                </div>
                <button
                  onClick={() => setSpec(null)}
                  className="shrink-0 rounded-lg p-1.5 text-text-lo hover:bg-white/5 hover:text-text-hi"
                  aria-label="Close"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="max-h-[calc(80vh-88px)] overflow-y-auto p-5">
                <div className="flex items-start gap-2.5 rounded-xl bg-surface-hi/60 p-3.5 text-xs">
                  <Database size={14} className="mt-0.5 shrink-0 text-accent-400" />
                  <div>
                    <div className="font-mono text-text-lo">{spec.sourceFile}</div>
                    <p className="mt-1 leading-relaxed text-text-lo">{spec.summary}</p>
                  </div>
                </div>

                <div className="mt-4 space-y-1.5">
                  {spec.rows.map((row, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm odd:bg-white/[0.02]"
                    >
                      <span className="text-text-lo">{row.label}</span>
                      {row.href ? (
                        <a
                          href={row.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 truncate font-mono text-xs text-accent-400 hover:underline"
                        >
                          {row.value} <ExternalLink size={11} className="shrink-0" />
                        </a>
                      ) : (
                        <span className="truncate font-mono text-xs text-text-hi">{row.value}</span>
                      )}
                    </div>
                  ))}
                  {spec.rows.length === 0 && (
                    <div className="py-6 text-center text-sm text-text-faint">No underlying rows to show.</div>
                  )}
                </div>

                {spec.moreCount !== undefined && spec.moreCount > 0 && (
                  <p className="mt-3 text-center text-xs text-text-faint">+{spec.moreCount} more rows not shown here</p>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </SourceInspectorContext.Provider>
  );
}
