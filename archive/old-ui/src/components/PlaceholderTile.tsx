import { gradientFor, initials } from "../lib/format";

interface PlaceholderTileProps {
  name: string;
  className?: string;
  textClassName?: string;
}

/**
 * Default visual for every corridor/society - not an apology state. No stock
 * photo is ever substituted and mislabeled as a specific named place (a real
 * risk checked and ruled out during this build: there is no reliable way to
 * verify a generic stock photo actually depicts a specific named locality).
 * A deterministic gradient + initials + a faint topographic-line pattern
 * (echoing the product's "mapping signal across a corridor" framing) reads as
 * intentional, not missing.
 */
export function PlaceholderTile({ name, className = "", textClassName = "text-3xl" }: PlaceholderTileProps) {
  const [from, to] = gradientFor(name);
  return (
    <div
      className={`relative flex items-center justify-center overflow-hidden ${className}`}
      style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}
    >
      <svg className="absolute inset-0 h-full w-full opacity-20" viewBox="0 0 200 200" preserveAspectRatio="none">
        {[30, 60, 90, 120, 150].map((y) => (
          <path key={y} d={`M0,${y} Q50,${y - 18} 100,${y} T200,${y}`} stroke="white" strokeWidth="1.4" fill="none" />
        ))}
      </svg>
      <span className={`relative font-display font-semibold text-white/90 drop-shadow-sm ${textClassName}`}>
        {initials(name)}
      </span>
    </div>
  );
}
