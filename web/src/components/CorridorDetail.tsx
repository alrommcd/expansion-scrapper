import { useEffect, useState } from "react";
import { BrokerTab } from "./BrokerTab";
import { ExplainPanel } from "./ExplainPanel";
import { NriTab } from "./NriTab";
import { SocietyTab } from "./SocietyTab";

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
  raw_metrics: {
    pct_units_in_band: number;
    min_distance_to_demand_anchor_km: number;
    rera_clean_pct: number;
    comp_count_90d: number;
    avg_dom_days: number;
    resale_txn_count_90d: number;
  };
}

type TabId = "society" | "broker" | "nri";

const TABS: { id: TabId; label: string }[] = [
  { id: "society", label: "Society" },
  { id: "broker", label: "Broker" },
  { id: "nri", label: "NRI Intelligence" },
];

interface CorridorDetailProps {
  cityId: string;
  corridor: string;
  onBack: () => void;
}

export function CorridorDetail({ cityId, corridor, onBack }: CorridorDetailProps) {
  const [city, setCity] = useState<City | null>(null);
  const [corridorData, setCorridorData] = useState<Corridor | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("society");

  useEffect(() => {
    fetch("/data/cities.json")
      .then((res) => res.json())
      .then((data: City[]) => setCity(data.find((c) => c.city_id === cityId) ?? null));
    fetch("/data/corridors.json")
      .then((res) => res.json())
      .then((data: Corridor[]) =>
        setCorridorData(data.find((c) => c.city_id === cityId && c.corridor === corridor) ?? null),
      );
  }, [cityId, corridor]);

  const cityName = city?.city_name ?? cityId;

  return (
    <div className="h-screen w-full overflow-y-auto bg-black text-white">
      {/*
        Horizontal hero placeholder - no per-corridor image asset exists
        yet, so this is a dark gradient with city + corridor name centered,
        not a broken/missing-image state.
      */}
      <div className="relative flex h-[34vh] min-h-[240px] w-full items-center justify-center overflow-hidden bg-gradient-to-b from-neutral-900 via-black to-black">
        <button
          type="button"
          onClick={onBack}
          className="absolute left-6 top-20 z-10 text-sm text-white/60 transition-colors duration-200 hover:text-lime-400 sm:left-10 sm:top-24"
        >
          &larr; Back to corridors
        </button>
        <div className="text-center">
          <p className="text-sm uppercase tracking-wide text-white/40">{cityName}</p>
          <h1 className="mt-1 text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">{corridor}</h1>
          {corridorData?.fit_score !== null && corridorData?.fit_score !== undefined && (
            <p className="mt-2 text-sm text-lime-400">Fit score {corridorData.fit_score.toFixed(1)}</p>
          )}
        </div>
      </div>

      <div className="border-b border-white/10 px-6 sm:px-10">
        <div className="flex gap-8">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`border-b-2 py-3 text-sm font-medium transition-colors duration-200 ${
                activeTab === tab.id
                  ? "border-lime-400 text-white"
                  : "border-transparent text-white/50 hover:text-white/80"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-6 py-8 sm:px-10">
        {activeTab === "society" && <SocietyTab cityId={cityId} corridor={corridor} />}
        {activeTab === "broker" && <BrokerTab cityId={cityId} corridor={corridor} />}
        {activeTab === "nri" && <NriTab cityId={cityId} cityName={cityName} corridor={corridor} />}
      </div>

      {corridorData && (
        <ExplainPanel
          title={`Why ${corridor} ranked here`}
          metrics={[
            { label: "Price-band fit", value: `${(corridorData.raw_metrics.pct_units_in_band * 100).toFixed(0)}% of units in band` },
            { label: "Demand-hub proximity", value: `${corridorData.raw_metrics.min_distance_to_demand_anchor_km} km away` },
            { label: "Clean title / RERA", value: `${(corridorData.raw_metrics.rera_clean_pct * 100).toFixed(0)}% RERA-clean` },
            { label: "Comp density", value: `${corridorData.raw_metrics.comp_count_90d} comps (90d)` },
            {
              label: "Resale velocity",
              value: `${corridorData.raw_metrics.avg_dom_days}d avg DOM, ${corridorData.raw_metrics.resale_txn_count_90d} txns (90d)`,
            },
          ]}
          note="Seed/placeholder scoring inputs for every city right now, not yet computed from live listing data - see PROGRESS.md."
        />
      )}
    </div>
  );
}
