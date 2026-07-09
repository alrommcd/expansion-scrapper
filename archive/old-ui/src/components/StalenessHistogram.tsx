import { motion } from "framer-motion";
import { useState } from "react";
import type { AbsenteeCandidate } from "../types";

const BUCKETS: { label: string; test: (d: number | null) => boolean }[] = [
  { label: "0-30d", test: (d) => d !== null && d <= 30 },
  { label: "31-60d", test: (d) => d !== null && d > 30 && d <= 60 },
  { label: "61-90d", test: (d) => d !== null && d > 60 && d <= 90 },
  { label: "90d+", test: (d) => d !== null && d > 90 },
  { label: "unknown", test: (d) => d === null },
];

/**
 * "Movement over time" as this data actually supports it: days_since_posted
 * is captured once per listing at scrape time, not from repeated
 * observations of the same listing - so this is a listing-age DISTRIBUTION
 * (how stale is the currently-flagged pool right now), never a trend line
 * implying we've watched these listings age over multiple visits. Binned bar
 * chart, not a smoothed density curve - the data is discrete counts in wide
 * buckets, drawing a continuous curve through that would imply precision
 * (a smooth underlying rate) the single-snapshot data doesn't have.
 */
export function StalenessHistogram({ candidates }: { candidates: AbsenteeCandidate[] }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const counts = BUCKETS.map((b) => ({
    label: b.label,
    count: candidates.filter((c) => b.test(c.days_since_posted)).length,
  }));
  const max = Math.max(1, ...counts.map((c) => c.count));
  const total = candidates.length;

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-display text-base font-medium text-text-hi">Listing age at time of scrape</h3>
        <span className="text-xs text-text-faint">days_since_posted, single snapshot</span>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-text-lo">
        A distribution, not a trend line: each listing's age was captured once, at scrape time, not tracked
        across repeat visits. Wider bars are honest here on purpose, this data doesn't support a smooth curve.
      </p>

      {total === 0 ? (
        <p className="mt-6 py-4 text-center text-sm text-text-faint">No candidates to distribute here.</p>
      ) : (
        <div className="mt-6 flex h-40 items-end gap-3">
          {counts.map((c, i) => {
            const heightPct = (c.count / max) * 100;
            return (
              <div
                key={c.label}
                className="flex flex-1 flex-col items-center gap-2"
                onMouseEnter={() => setHovered(c.label)}
                onMouseLeave={() => setHovered((h) => (h === c.label ? null : h))}
              >
                <div className="relative flex h-28 w-full items-end justify-center">
                  {hovered === c.label && (
                    <div className="absolute -top-7 whitespace-nowrap rounded-md bg-surface-hi px-2 py-1 font-mono text-[11px] text-text-hi shadow-lg">
                      {c.count} of {total}
                    </div>
                  )}
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: c.count === 0 ? 2 : `${Math.max(heightPct, 4)}%` }}
                    transition={{ duration: 0.5, delay: i * 0.05, ease: [0.16, 1, 0.3, 1] }}
                    className={`w-full max-w-[36px] rounded-t-md bg-accent-500 transition-opacity ${
                      hovered && hovered !== c.label ? "opacity-40" : "opacity-100"
                    } ${c.count === 0 ? "bg-surface-hi" : ""}`}
                  />
                </div>
                <span className="font-mono tabular text-[11px] text-text-hi">{c.count}</span>
                <span className="text-[11px] text-text-lo">{c.label}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
