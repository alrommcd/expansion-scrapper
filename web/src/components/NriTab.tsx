import { ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";

interface AbsenteeCandidate {
  city_id: string;
  corridor: string;
  society: string;
  signal_matched: string;
  score: string;
  days_since_posted: number;
  evidence: string;
  detail_url: string | null;
  traceable: boolean;
}

interface DirectoryEntry {
  platform: string;
  group_name: string;
  link: string;
  category: string;
  city_focus: string;
}

const SIGNAL_LABELS: Record<string, string> = {
  multi_property_owner: "Multiple properties, one owner",
  never_occupied: "Never-occupied listing language",
};

// nri_directory.json's only location field, confirmed live: 52 of 73 rows
// (71%) have city_focus="" (no city at all), the rest are inconsistent free
// text with typos, and several aren't one of our 5 cities (Coimbatore,
// Dubai, Zanzibar...). It has no corridor field at all - Pune and Chennai
// have zero city-level matches, let alone corridor-level ones. Per explicit
// decision: show the full directory regardless of city/corridor, with rows
// matching the current city (fuzzy-matched for the typos actually observed
// in the data, not hypothetical ones) sorted first - not filtered down to
// an empty state.
const CITY_FOCUS_ALIASES: Record<string, string> = {
  bangalore: "bangalore",
  banglore: "bangalore",
  blr: "bangalore",
  hyderabad: "hyderabad",
  mumbai: "mumbai",
  pune: "pune",
  chennai: "chennai",
};

function matchesCity(cityFocus: string, cityId: string): boolean {
  const normalized = CITY_FOCUS_ALIASES[cityFocus.trim().toLowerCase()];
  return normalized === cityId;
}

export function NriTab({ cityId, cityName, corridor }: { cityId: string; cityName: string; corridor: string }) {
  const [candidates, setCandidates] = useState<AbsenteeCandidate[] | null>(null);
  const [directory, setDirectory] = useState<DirectoryEntry[] | null>(null);

  useEffect(() => {
    fetch("/data/absentee_candidates.json")
      .then((res) => res.json())
      .then((data: AbsenteeCandidate[]) =>
        setCandidates(data.filter((c) => c.city_id === cityId && c.corridor === corridor)),
      );
    fetch("/data/nri_directory.json")
      .then((res) => res.json())
      .then((data: DirectoryEntry[]) => {
        const sorted = [...data].sort((a, b) => {
          const aMatch = matchesCity(a.city_focus, cityId) ? 1 : 0;
          const bMatch = matchesCity(b.city_focus, cityId) ? 1 : 0;
          return bMatch - aMatch;
        });
        setDirectory(sorted);
      });
  }, [cityId, corridor]);

  return (
    <div className="space-y-10">
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-white/50">
          Absentee / NRI-likelihood candidates
        </h2>
        {candidates === null ? (
          <p className="mt-3 text-sm text-white/50">Loading...</p>
        ) : candidates.length === 0 ? (
          <p className="mt-3 text-sm text-white/50">No flagged candidates for this corridor yet.</p>
        ) : (
          <>
            <p className="mt-1 text-[11px] text-white/35">
              A heuristic proxy from listing text, not confirmed identity or ownership.
            </p>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {candidates.map((c, i) => (
                <div key={i} className="rounded-sm border border-white/15 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-medium text-white">{c.society}</h3>
                    <span className="shrink-0 rounded-sm border border-lime-400/40 px-2 py-0.5 text-xs font-semibold text-lime-400">
                      score {c.score}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-white/70">
                    {SIGNAL_LABELS[c.signal_matched] ?? c.signal_matched}
                  </p>
                  <p className="mt-2 text-[11px] text-white/40">{c.evidence}</p>
                  <p className="mt-1 text-[11px] text-white/30">Posted {c.days_since_posted}d ago</p>
                  {c.traceable && c.detail_url ? (
                    <a
                      href={c.detail_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex items-center gap-1 text-[11px] text-white/45 hover:text-lime-400"
                    >
                      <ExternalLink size={11} /> View listing
                    </a>
                  ) : (
                    <p className="mt-2 text-[11px] text-white/25">Not traceable - no detail URL captured at scrape time</p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-white/50">Community directory</h2>
        <p className="mt-1 text-[11px] text-white/35">
          General, city-wide NRI/real-estate group directory (not scoped to {corridor} specifically - this data
          has no corridor-level detail) - {cityName}-tagged links are listed first where they exist.
        </p>
        {directory === null ? (
          <p className="mt-3 text-sm text-white/50">Loading...</p>
        ) : (
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {directory.map((d, i) => {
              const isMatch = matchesCity(d.city_focus, cityId);
              return (
                <a
                  key={i}
                  href={d.link}
                  target="_blank"
                  rel="noreferrer"
                  className={`rounded-sm border p-3 text-sm transition-colors duration-200 hover:border-lime-400 ${
                    isMatch ? "border-lime-400/40" : "border-white/15"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-white/90">{d.group_name || d.platform}</span>
                    {isMatch && (
                      <span className="shrink-0 rounded-sm bg-lime-400/15 px-1.5 py-0.5 text-[10px] text-lime-400">
                        {cityName}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-[11px] text-white/40">
                    {d.platform} - {d.category}
                  </p>
                </a>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
