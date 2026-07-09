import { ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";

// Fields read directly from societies.json - confirmed live: rating_available
// and detail_available are false for every one of the 128 rows right now (no
// GOOGLE_MAPS_API_KEY set upstream), so rating/review_count/unit_count/
// possession_status/rera_number/sales_contact/project_description/
// official_url are null across the board. Not shown per-field (would just be
// a wall of "Unavailable" labels) - a single note covers it instead.
interface Society {
  city_id: string;
  corridor: string;
  society_display: string;
  supply_depth: number;
  resale_velocity_days: number;
  price_consistency_cov: number;
  rating: number | null;
  society_fit_score: number;
  candidate_count: number;
  detail_available: boolean;
  sample_detail_url: string | null;
}

export function SocietyTab({ cityId, corridor }: { cityId: string; corridor: string }) {
  const [societies, setSocieties] = useState<Society[] | null>(null);

  useEffect(() => {
    fetch("/data/societies.json")
      .then((res) => res.json())
      .then((data: Society[]) =>
        setSocieties(data.filter((s) => s.city_id === cityId && s.corridor === corridor)),
      );
  }, [cityId, corridor]);

  if (societies === null) {
    return <p className="text-sm text-white/50">Loading societies...</p>;
  }

  if (societies.length === 0) {
    return <p className="text-sm text-white/50">No scored societies for this corridor yet.</p>;
  }

  const sorted = [...societies].sort((a, b) => b.society_fit_score - a.society_fit_score);

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {sorted.map((s) => (
        <div key={s.society_display} className="rounded-sm border border-white/15 p-4">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-medium text-white">{s.society_display}</h3>
            <span className="shrink-0 rounded-sm border border-lime-400/40 px-2 py-0.5 text-sm font-semibold text-lime-400">
              {s.society_fit_score.toFixed(1)}
            </span>
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs text-white/70">
            <dt className="text-white/40">Supply depth</dt>
            <dd>{s.supply_depth} listings</dd>
            <dt className="text-white/40">Resale velocity</dt>
            <dd>{s.resale_velocity_days > 0 ? `${s.resale_velocity_days.toFixed(0)}d` : "N/A"}</dd>
            <dt className="text-white/40">Price consistency</dt>
            <dd>{(s.price_consistency_cov * 100).toFixed(0)}% CoV</dd>
            <dt className="text-white/40">Absentee candidates</dt>
            <dd>{s.candidate_count}</dd>
          </dl>
          {!s.detail_available && (
            <p className="mt-3 border-t border-white/10 pt-2 text-[11px] text-white/35">
              Rating and listing detail not verified for this society.
            </p>
          )}
          {s.sample_detail_url && (
            <a
              href={s.sample_detail_url}
              target="_blank"
              rel="noreferrer"
              title="One real listing used to identify this society - an example to verify, not the full basis for its score"
              className="mt-2 inline-flex items-center gap-1 text-[11px] text-white/45 hover:text-lime-400"
            >
              <ExternalLink size={11} /> Sample listing
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
