import { motion } from "framer-motion";
import { AlertTriangle, Building2, ChevronDown, Search, Star } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Breadcrumb } from "../components/Breadcrumb";
import { ImageTile } from "../components/ImageTile";
import { LoadingState } from "../components/LoadingState";
import { NotScoredState } from "../components/NotScoredState";
import { ScoreRing } from "../components/ScoreRing";
import { useSourceInspector } from "../components/SourceInspector";
import { useAppData } from "../data/DataProvider";
import { formatCov, formatDays, plural } from "../lib/format";
import { societyKey } from "../lib/images";
import type { Society } from "../types";

type SortKey = "society_fit_score" | "supply_depth" | "resale_velocity_days" | "rating";
const SORT_OPTIONS: [SortKey, string][] = [
  ["society_fit_score", "Fit score"],
  ["supply_depth", "Supply depth"],
  ["resale_velocity_days", "Resale velocity"],
  ["rating", "Rating"],
];

const cardContainer = { hidden: {}, show: { transition: { staggerChildren: 0.04 } } };
const cardItem = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const } },
};

function societyReasons(s: Society): string[] {
  const reasons: string[] = [`${s.supply_depth} in-band listing${s.supply_depth === 1 ? "" : "s"}`];
  if (s.resale_velocity_days !== null) reasons.push(`resale in ~${Math.round(s.resale_velocity_days)}d`);
  else if (s.rating_available) reasons.push(`${s.rating?.toFixed(1)}★ (${s.review_count} reviews)`);
  return reasons.slice(0, 2);
}

export function SocietyFinder() {
  const { cityId, corridorName } = useParams<{ cityId: string; corridorName: string }>();
  const { data, loading } = useAppData();
  const [sortKey, setSortKey] = useState<SortKey>("society_fit_score");
  const [query, setQuery] = useState("");
  const openSource = useSourceInspector();

  const city = data?.cities.find((c) => c.city_id === cityId);
  const corridor = data?.corridors.find((c) => c.city_id === cityId && c.corridor === corridorName);

  const societies = useMemo(() => {
    let rows = (data?.societies ?? []).filter((s) => s.city_id === cityId && s.corridor === corridorName);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      rows = rows.filter((s) => s.society_display.toLowerCase().includes(q));
    }
    return [...rows].sort((a, b) => (b[sortKey] ?? -Infinity) - (a[sortKey] ?? -Infinity));
  }, [data, cityId, corridorName, query, sortKey]);

  if (loading) return <LoadingState />;
  if (!city || !corridor) return null;

  const crumbs = [
    { label: "Home", to: "/" },
    { label: "City Explorer", to: "/explore" },
    { label: city.city_name, to: `/city/${cityId}` },
    { label: corridor.corridor, to: `/city/${cityId}/corridor/${encodeURIComponent(corridor.corridor)}` },
    { label: "Society Finder" },
  ];

  if (!city.has_price_band) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-10">
        <Breadcrumb items={crumbs} />
        <h1 className="font-display text-2xl font-semibold text-text-hi">Society Finder</h1>
        <div className="mt-8">
          <NotScoredState
            icon={Star}
            title="Not scored yet"
            reason={`No product price band configured for ${city.city_name}. Society-fit scoring needs a HouseEazy-confirmed price range in this city's config before it can compute supply depth, velocity, or consistency. Corridor ranking and Broker Finder are unaffected.`}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-10">
      <Breadcrumb items={crumbs} />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <motion.div layoutId="tile-icon-Society Finder" className="rounded-xl bg-accent-500/15 p-3 text-accent-300">
            <Building2 size={22} strokeWidth={1.75} />
          </motion.div>
          <div>
            <h1 className="font-display text-2xl font-semibold text-text-hi">Society Finder</h1>
            <p className="mt-1 text-sm text-text-lo">
              {plural(societies.length, "society", "societies")} in {corridor.corridor}, ranked by society_fit_score
              (percentile rank within {city.city_name}, never a fixed threshold).
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="glass-hi flex items-center gap-2 rounded-xl px-3 py-2">
            <Search size={16} className="text-text-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter societies..."
              className="w-40 bg-transparent text-sm text-text-hi outline-none placeholder:text-text-faint"
            />
          </div>
          <div className="glass-hi relative flex items-center gap-2 rounded-xl px-3 py-2">
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="appearance-none bg-transparent pr-5 text-sm text-text-hi outline-none [&>option]:bg-surface-hi"
            >
              {SORT_OPTIONS.map(([key, label]) => (
                <option key={key} value={key}>
                  Sort: {label}
                </option>
              ))}
            </select>
            <ChevronDown size={13} className="pointer-events-none absolute right-3 text-text-faint" />
          </div>
        </div>
      </div>

      <motion.div
        className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3"
        initial="hidden"
        animate="show"
        variants={cardContainer}
      >
        {societies.map((s) => (
          <SocietyCard key={s.society_normalized} society={s} cityName={city.city_name} openSource={openSource} />
        ))}
      </motion.div>
      {societies.length === 0 && <div className="py-12 text-center text-sm text-text-lo">No societies match.</div>}
    </div>
  );
}

function SocietyCard({
  society: s,
  cityName,
  openSource,
}: {
  society: Society;
  cityName: string;
  openSource: ReturnType<typeof useSourceInspector>;
}) {
  const reasons = societyReasons(s);

  const openDetail = () =>
    openSource({
      title: s.society_display,
      sourceFile: "scoring/society_fit.py + scoring/society_enrichment.py -> web/public/data/societies.json",
      summary:
        "Existing metrics (society_fit_score's 4 inputs, percentile rank within this city) plus whatever the separate detail-enrichment step resolved from a confidently-matched official project page. Enrichment fields stay unavailable, never guessed, when no confident source was found.",
      rows: [
        { label: "Fit score", value: s.society_fit_score !== null ? s.society_fit_score.toFixed(1) : "not scored" },
        { label: "Supply depth", value: `${s.supply_depth} in-band listings` },
        { label: "Resale velocity", value: formatDays(s.resale_velocity_days) },
        { label: "Price consistency", value: formatCov(s.price_consistency_cov) },
        {
          label: "Google Maps rating",
          value: s.rating_available ? `${s.rating?.toFixed(1)} (${s.review_count} reviews)` : "unavailable",
        },
        { label: "Linked absentee candidates", value: `${s.candidate_count}` },
        {
          label: "Also appears in",
          value: s.appears_in_corridors.filter((c) => c).join(", ") || "this corridor only",
        },
        ...(s.detail_available
          ? [
              { label: "Unit count", value: s.unit_count ?? "not found on page" },
              { label: "Possession status", value: s.possession_status ?? "not found on page" },
              { label: "RERA number", value: s.rera_number ?? "not found on page" },
              { label: "Sales contact", value: s.sales_contact ?? "not found on page" },
              { label: "Description", value: s.project_description ?? "not found on page" },
              ...(s.official_url ? [{ label: "Official page", value: "open source", href: s.official_url }] : []),
            ]
          : [{ label: "Project detail enrichment", value: s.detail_confidence_note ?? "unavailable, no confident match" }]),
      ],
    });

  return (
    <motion.div
      variants={cardItem}
      className="glass flex flex-col overflow-hidden rounded-2xl transition-all hover:-translate-y-1 hover:border-accent-500/40 hover:shadow-xl hover:shadow-accent-900/40"
    >
      <div className="group relative">
        <ImageTile
          name={s.society_display}
          bucket="societies"
          manifestKey={societyKey(cityName, s.corridor, s.society_display)}
          className="h-36 w-full"
          showIllustrativeTag
        />
      </div>

      <div className="flex flex-1 flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <button
              onClick={openDetail}
              className="truncate font-display text-base font-medium text-text-hi underline decoration-transparent underline-offset-2 transition-colors hover:decoration-accent-400"
              title="View society details"
            >
              {s.society_display}
            </button>
            {s.appears_in_corridors.length > 1 && (
              <div className="mt-1 flex items-center gap-1 text-[11px] text-amber-400">
                <AlertTriangle size={11} className="shrink-0" />
                Also in {s.appears_in_corridors.filter((c) => c).length - 1} other corridor(s)
              </div>
            )}
          </div>
          <button
            onClick={openDetail}
            className="shrink-0 rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500"
            aria-label={`View details for ${s.society_display}`}
          >
            <ScoreRing kind="society" value={s.society_fit_score} size={48} showLabel={false} />
          </button>
        </div>

        <ul className="space-y-1 text-xs text-text-lo">
          {reasons.map((r) => (
            <li key={r} className="flex items-center gap-1.5">
              <span className="h-1 w-1 shrink-0 rounded-full bg-accent-400" />
              {r}
            </li>
          ))}
        </ul>

        <div className="mt-auto pt-1">
          {s.candidate_count > 0 ? (
            <Link
              to={`/city/${s.city_id}/corridor/${encodeURIComponent(s.corridor)}/absentee`}
              className="inline-block rounded-full bg-accent-500/15 px-2.5 py-1 text-xs font-medium text-accent-300 hover:bg-accent-500/25"
            >
              {s.candidate_count} candidate{s.candidate_count === 1 ? "" : "s"} flagged
            </Link>
          ) : (
            <span className="text-xs text-text-faint">No candidates flagged</span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
