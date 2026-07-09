import { useEffect, useState } from "react";
import { ExplainPanel } from "./ExplainPanel";

interface City {
  city_id: string;
  city_name: string;
  state: string;
}

interface Corridor {
  city_id: string;
  corridor: string;
  eligible: boolean;
  failed_gates: string[];
  fit_score: number | null;
  sub_scores: Record<string, number>;
}

const GATE_LABELS: Record<string, string> = {
  product_in_band: "Price-band fit",
  demand_adjacent: "Demand-hub proximity",
  clean_title: "Clean title / RERA",
  comp_density: "Comp density",
  resale_velocity: "Resale velocity",
};

interface CorridorListProps {
  cityId: string;
  onSelectCorridor: (corridor: string) => void;
  onBack: () => void;
}

export function CorridorList({ cityId, onSelectCorridor, onBack }: CorridorListProps) {
  const [city, setCity] = useState<City | null>(null);
  const [corridors, setCorridors] = useState<Corridor[] | null>(null);
  // Naming convention: web/public/images/cities/<city_id>.jpg, city_id
  // matching cities.json exactly (pune/mumbai/bangalore/hyderabad/chennai).
  // Drop a new file at that path and it picks it up with no code change.
  // Falls back to the plain black background (no broken-image glyph) via
  // onError below if a city's file is ever missing - not a hard dependency.
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
  }, [cityId]);

  useEffect(() => {
    fetch("/data/cities.json")
      .then((res) => res.json())
      .then((data: City[]) => setCity(data.find((c) => c.city_id === cityId) ?? null));
    fetch("/data/corridors.json")
      .then((res) => res.json())
      .then((data: Corridor[]) => setCorridors(data.filter((c) => c.city_id === cityId)));
  }, [cityId]);

  const cityName = city?.city_name ?? cityId;

  const sorted = corridors
    ? [...corridors].sort((a, b) => {
        if (a.eligible !== b.eligible) return a.eligible ? -1 : 1;
        return (b.fit_score ?? 0) - (a.fit_score ?? 0);
      })
    : null;

  return (
    <div className="relative h-screen w-full overflow-y-auto bg-black text-white">
      {/*
        Full-bleed landmark background, well behind the content layer
        (z-0 vs content's z-10) - opacity + a dark gradient scrim + a
        saturation/brightness pull-down so it reads as atmosphere behind
        the page rather than a bright photo sitting on top of it. Same
        glass-panel instinct as IndiaMap's city labels, just applied to a
        whole-screen backdrop instead of a small tag.
      */}
      <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        {!imageFailed && (
          <img
            src={`/images/cities/${cityId}.jpg`}
            alt=""
            onError={() => setImageFailed(true)}
            className="h-full w-full object-cover opacity-90"
            style={{ filter: "saturate(0.55) brightness(0.8)" }}
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-b from-black via-black/55 to-black" />
        <div className="absolute inset-0 bg-black/35" />
      </div>

      <div className="relative z-10 px-6 pt-24 sm:px-10 sm:pt-28">
        <button
          type="button"
          onClick={onBack}
          className="text-sm text-white/60 transition-colors duration-200 hover:text-lime-400"
        >
          &larr; Back to map
        </button>
        <h1 className="mt-6 text-3xl font-bold tracking-tight sm:text-4xl">{cityName}</h1>
        <p className="mt-1 text-sm text-white/50">
          {sorted ? `${sorted.length} corridors` : "Loading corridors..."}
        </p>
      </div>

      <div className="relative z-10 px-6 py-8 sm:px-10">
        {sorted === null ? (
          <p className="text-sm text-white/50">Loading...</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sorted.map((c) => (
              <button
                key={c.corridor}
                type="button"
                onClick={() => c.eligible && onSelectCorridor(c.corridor)}
                disabled={!c.eligible}
                className={`rounded-sm border p-4 text-left backdrop-blur-sm transition-colors duration-200 ${
                  c.eligible
                    ? "border-white/15 bg-black/50 hover:border-lime-400/50 cursor-pointer"
                    : "border-white/5 bg-black/50 opacity-50 cursor-not-allowed"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-medium text-white">{c.corridor}</h3>
                  {c.fit_score !== null ? (
                    <span className="shrink-0 rounded-sm border border-lime-400/40 px-2 py-0.5 text-sm font-semibold text-lime-400">
                      {c.fit_score.toFixed(1)}
                    </span>
                  ) : (
                    <span className="shrink-0 rounded-sm border border-white/20 px-2 py-0.5 text-xs text-white/40">
                      N/A
                    </span>
                  )}
                </div>
                {c.eligible ? (
                  <p className="mt-2 text-xs text-white/40">Eligible - all 5 gates passed</p>
                ) : (
                  <p className="mt-2 text-xs text-white/40">
                    Ineligible - failed: {c.failed_gates.map((g) => GATE_LABELS[g] ?? g).join(", ")}
                  </p>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      <ExplainPanel
        title="How corridors are ranked"
        metrics={[
          { label: "Price-band fit", value: "share of units in target price range" },
          { label: "Demand-hub proximity", value: "distance to nearest employment hub" },
          { label: "Clean title / RERA", value: "share of RERA-registered listings" },
          { label: "Comp density", value: "comparable listings available (90d)" },
          { label: "Resale velocity", value: "days-on-market + resale transaction volume" },
        ]}
        note="5 equal-weighted gates. Scoring inputs are seed/placeholder values for every city right now, not yet computed from live listing data - see a specific corridor's panel for its actual numbers."
      />
    </div>
  );
}
