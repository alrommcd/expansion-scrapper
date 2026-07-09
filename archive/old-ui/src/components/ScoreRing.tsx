import { motion, useReducedMotion } from "framer-motion";
import type { ScoreKind } from "../types";

const KIND_COLOR: Record<ScoreKind, string> = {
  corridor: "var(--color-signal-corridor)",
  society: "var(--color-signal-society)",
  broker: "var(--color-signal-broker)",
};

const KIND_LABEL: Record<ScoreKind, string> = {
  corridor: "Fit",
  society: "Society fit",
  broker: "Activity",
};

interface ScoreRingProps {
  kind: ScoreKind;
  value: number | null; // 0-10 scale, or null when genuinely not scored
  size?: number;
  unavailableReason?: string;
  showLabel?: boolean;
}

/**
 * The one visual motif every score in this product shares: a circular arc,
 * color-coded by score TYPE, never by value. Corridor fit_score, society_fit_score,
 * and broker_activity_score always render in their own color so a user learns to
 * tell them apart by shape/color alone - reinforcing that these are four
 * structurally separate numbers, never a single blended metric.
 *
 * `value === null` renders a dashed, colorless ring and "Not scored" - never a
 * fabricated 0, which would visually claim "scored, and scored badly."
 */
export function ScoreRing({ kind, value, size = 88, unavailableReason, showLabel = true }: ScoreRingProps) {
  const reduceMotion = useReducedMotion();
  const stroke = size * 0.09;
  const radius = size / 2 - stroke;
  const circumference = 2 * Math.PI * radius;
  const pct = value === null ? 0 : Math.max(0, Math.min(1, value / 10));
  const color = KIND_COLOR[kind];

  return (
    <div className="inline-flex flex-col items-center gap-2" title={value === null ? unavailableReason : undefined}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--color-surface-hi)"
            strokeWidth={stroke}
          />
          {value !== null && (
            <motion.circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: circumference * (1 - pct) }}
              transition={reduceMotion ? { duration: 0 } : { duration: 1.1, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
            />
          )}
          {value === null && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="var(--color-text-faint)"
              strokeWidth={stroke * 0.6}
              strokeDasharray="3 6"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {value !== null ? (
            <span className="font-mono font-semibold tabular text-lg" style={{ color }}>
              {value.toFixed(1)}
            </span>
          ) : (
            <span className="font-mono text-[10px] text-text-faint uppercase tracking-wide">N/A</span>
          )}
        </div>
      </div>
      {showLabel && (
        <span className="text-xs text-text-lo uppercase tracking-wider">
          {value === null ? "Not scored" : KIND_LABEL[kind]}
        </span>
      )}
    </div>
  );
}
