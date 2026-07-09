import { motion } from "framer-motion";
import { useState } from "react";
import { Link } from "react-router-dom";

export interface CorridorSignalRow {
  corridor: string;
  count: number;
}

/**
 * "Movement across corridors": where the absentee-candidate signal
 * concentrates within a city, drawn from data.candidates grouped by
 * corridor - not a mock. Sequential single-hue bar chart (the job here is
 * "compare magnitude, low to high", not identity, so one hue is the honest
 * choice per the dataviz form heuristic - a categorical palette per corridor
 * would imply the corridors are being compared as distinct series rather
 * than ranked on one measure).
 */
export function CorridorSignalChart({ cityId, rows }: { cityId: string; rows: CorridorSignalRow[] }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const max = Math.max(1, ...rows.map((r) => r.count));
  const sorted = [...rows].sort((a, b) => b.count - a.count);
  const allZero = sorted.every((r) => r.count === 0);

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-display text-base font-medium text-text-hi">Candidates by corridor</h3>
        <span className="text-xs text-text-faint">absentee_candidates.json, grouped by corridor</span>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-text-lo">
        Flagged candidate count per corridor, this city. Bar length is a raw count, not a rate - a corridor
        with more total listings will naturally show more candidates.
      </p>

      {allZero ? (
        <p className="mt-6 py-4 text-center text-sm text-text-faint">No candidates flagged in any corridor here.</p>
      ) : (
        <div className="mt-5 space-y-2.5">
          {sorted.map((r, i) => {
            const pct = (r.count / max) * 100;
            return (
              <Link
                key={r.corridor}
                to={`/city/${cityId}/corridor/${encodeURIComponent(r.corridor)}/absentee`}
                className="block"
                onMouseEnter={() => setHovered(r.corridor)}
                onMouseLeave={() => setHovered((h) => (h === r.corridor ? null : h))}
              >
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="truncate text-text-lo">{r.corridor}</span>
                  <span className="font-mono tabular text-text-hi">{r.count}</span>
                </div>
                <div className="relative h-[18px] rounded-full bg-surface-hi">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.6, delay: i * 0.04, ease: [0.16, 1, 0.3, 1] }}
                    className={`h-full rounded-full bg-accent-500 transition-opacity ${
                      hovered && hovered !== r.corridor ? "opacity-40" : "opacity-100"
                    }`}
                  />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
