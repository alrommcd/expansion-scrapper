import { motion } from "framer-motion";
import { AlertTriangle, ArrowRight, BarChart3, ListOrdered } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Breadcrumb } from "../components/Breadcrumb";
import { CorridorSignalChart } from "../components/CorridorSignalChart";
import { ImageTile } from "../components/ImageTile";
import { LoadingState } from "../components/LoadingState";
import { ScoreRing } from "../components/ScoreRing";
import { useSourceInspector } from "../components/SourceInspector";
import { StalenessHistogram } from "../components/StalenessHistogram";
import { useAppData } from "../data/DataProvider";
import { corridorKey } from "../lib/images";
import type { AbsenteeCandidate, Broker, Corridor, Society } from "../types";

const corridorContainer = { hidden: {}, show: { transition: { staggerChildren: 0.04 } } };
const corridorItem = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const } },
};

function corridorReasons(
  corridor: Corridor,
  societies: Society[],
  brokers: Broker[],
  candidates: AbsenteeCandidate[]
): string[] {
  const reasons: string[] = [];
  reasons.push(
    corridor.eligible
      ? "Passed all 5 fit gates"
      : `Failed ${corridor.failed_gates.length} of 5 fit gates`
  );
  reasons.push(`${societies.length} ${societies.length === 1 ? "society" : "societies"} tracked`);
  reasons.push(`${brokers.length} ${brokers.length === 1 ? "broker" : "brokers"} active`);
  if (candidates.length > 0) {
    const ages = candidates.map((c) => c.days_since_posted).filter((d): d is number => d !== null);
    const freshest = ages.length > 0 ? Math.min(...ages) : null;
    reasons.push(
      `${candidates.length} candidate${candidates.length === 1 ? "" : "s"} flagged` +
        (freshest !== null ? `, freshest ${freshest}d ago` : "")
    );
  } else {
    reasons.push("0 candidates flagged");
  }
  return reasons;
}

export function CityView() {
  const { cityId } = useParams<{ cityId: string }>();
  const { data, loading } = useAppData();
  const openSource = useSourceInspector();
  const [view, setView] = useState<"ranked" | "distribution">("ranked");

  const city = data?.cities.find((c) => c.city_id === cityId);
  const corridors = data?.corridors.filter((c) => c.city_id === cityId) ?? [];
  const ranked = [...corridors].sort((a, b) => (b.fit_score ?? -1) - (a.fit_score ?? -1));
  const cityCandidates = data?.candidates.filter((c) => c.city_id === cityId) ?? [];
  const citySocieties = data?.societies.filter((s) => s.city_id === cityId) ?? [];
  const cityBrokers = data?.brokers.filter((b) => b.city_id === cityId) ?? [];
  const signalRows = corridors.map((c) => ({
    corridor: c.corridor,
    count: cityCandidates.filter((cand) => cand.corridor === c.corridor).length,
  }));

  if (loading) return <LoadingState />;
  if (!city) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-16 text-center">
        <p className="text-text-lo">City "{cityId}" is not registered in the engine.</p>
        <Link to="/explore" className="mt-4 inline-block text-accent-400 hover:underline">
          Back to City Explorer
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-10">
      <Breadcrumb items={[{ label: "Home", to: "/" }, { label: "City Explorer", to: "/explore" }, { label: city.city_name }]} />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-hi">{city.city_name}</h1>
          <p className="mt-1 text-sm text-text-lo">
            Corridors ranked by fit_score, the locked 5-gate engine. Click a corridor to see its societies.
          </p>
        </div>
        <div className="glass-hi flex items-center gap-1 rounded-xl p-1">
          <button
            onClick={() => setView("ranked")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              view === "ranked" ? "bg-accent-500/20 text-text-hi" : "text-text-lo hover:text-text-hi"
            }`}
          >
            <ListOrdered size={13} /> Ranked
          </button>
          <button
            onClick={() => setView("distribution")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              view === "distribution" ? "bg-accent-500/20 text-text-hi" : "text-text-lo hover:text-text-hi"
            }`}
          >
            <BarChart3 size={13} /> Distribution
          </button>
        </div>
      </div>

      {!city.has_price_band && (
        <div className="glass mt-5 flex items-start gap-3 rounded-xl border border-amber-500/20 p-4 text-sm">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-400" />
          <span className="text-text-lo">
            No product price band is configured for {city.city_name} yet, so the Society Finder tab will
            show a "not scored" state rather than a fit table. Corridor ranking and Broker Finder are
            unaffected.
          </span>
        </div>
      )}

      {view === "distribution" ? (
        cityCandidates.length > 0 ? (
          <div className="mt-8 grid grid-cols-1 gap-5 lg:grid-cols-2">
            <CorridorSignalChart cityId={cityId ?? ""} rows={signalRows} />
            <StalenessHistogram candidates={cityCandidates} />
          </div>
        ) : (
          <div className="glass mt-8 rounded-2xl px-8 py-16 text-center text-sm text-text-lo">
            No candidates flagged in {city.city_name} yet - nothing to distribute.
          </div>
        )
      ) : (
        <motion.div className="mt-8 space-y-4" initial="hidden" animate="show" variants={corridorContainer}>
          {ranked.map((corridor, i) => {
            const corridorSocieties = citySocieties.filter((s) => s.corridor === corridor.corridor);
            const corridorBrokers = cityBrokers.filter((b) => b.corridor === corridor.corridor);
            const corridorCandidates = cityCandidates.filter((c) => c.corridor === corridor.corridor);
            const reasons = corridorReasons(corridor, corridorSocieties, corridorBrokers, corridorCandidates);

            return (
              <motion.div key={corridor.corridor} variants={corridorItem}>
                <Link
                  to={`/city/${cityId}/corridor/${encodeURIComponent(corridor.corridor)}/society`}
                  className="glass group flex flex-col overflow-hidden rounded-2xl transition-all hover:-translate-y-0.5 hover:border-accent-500/40 hover:shadow-xl hover:shadow-accent-900/40 sm:flex-row"
                >
                  <div className="relative h-32 w-full shrink-0 sm:h-auto sm:w-56">
                    <ImageTile
                      name={corridor.corridor}
                      bucket="corridors"
                      manifestKey={corridorKey(city.city_name, corridor.corridor)}
                      className="h-full w-full"
                      showIllustrativeTag
                    />
                    <span className="absolute left-3 top-3 flex h-7 w-7 items-center justify-center rounded-full bg-void/70 font-mono text-xs font-semibold text-text-hi backdrop-blur-sm">
                      #{i + 1}
                    </span>
                  </div>

                  <div className="flex flex-1 items-center justify-between gap-4 p-5">
                    <div className="min-w-0">
                      <div className="truncate font-display text-base font-medium text-text-hi">{corridor.corridor}</div>
                      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-lo">
                        {reasons.map((r) => (
                          <li key={r} className="flex items-center gap-1.5">
                            <span className="h-1 w-1 shrink-0 rounded-full bg-accent-400" />
                            {r}
                          </li>
                        ))}
                      </ul>
                      <div className="mt-3 flex items-center gap-1 text-sm text-accent-400 opacity-0 transition-opacity group-hover:opacity-100">
                        View societies <ArrowRight size={13} />
                      </div>
                    </div>
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label={`Inspect source for ${corridor.corridor}'s fit score`}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        openSource({
                          title: `${corridor.corridor} - fit_score`,
                          sourceFile: "scoring/corridor.py rank_corridors() -> web/public/data/corridors.json",
                          summary:
                            "The locked 5-gate engine: a corridor must clear all 5 gates to be eligible, then survivors are ranked by an equal-weighted composite of the 5 normalized sub-scores below. Ineligible corridors show no fit_score, never a fabricated 0.",
                          rows: [
                            { label: "Eligible", value: corridor.eligible ? "yes, all 5 gates passed" : "no" },
                            ...(corridor.eligible
                              ? Object.entries(corridor.sub_scores).map(([k, v]) => ({
                                  label: k,
                                  value: typeof v === "number" ? v.toFixed(2) : String(v),
                                }))
                              : [{ label: "Failed gates", value: corridor.failed_gates.join(", ") || "none listed" }]),
                            { label: "Absentee candidates linked", value: `${corridorCandidates.length}` },
                          ],
                        });
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          (e.currentTarget as HTMLElement).click();
                        }
                      }}
                      className="shrink-0 cursor-pointer rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500"
                    >
                      <ScoreRing
                        kind="corridor"
                        value={corridor.fit_score}
                        size={64}
                        showLabel={false}
                        unavailableReason={`Failed: ${corridor.failed_gates.join(", ")}`}
                      />
                    </span>
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </div>
  );
}
