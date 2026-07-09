import { motion } from "framer-motion";
import { AlertCircle, Info, MessagesSquare, ScanSearch } from "lucide-react";
import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { Breadcrumb } from "../components/Breadcrumb";
import { LoadingState } from "../components/LoadingState";
import { PipelineLineage } from "../components/PipelineLineage";
import { useAppData } from "../data/DataProvider";
import { plural } from "../lib/format";

// No entrance animation existed on these candidate cards before this pass -
// added fresh with the same staggerChildren/delayChildren pattern used
// across the rest of the app.
const candidateContainer = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } };
const candidateItem = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const } },
};

export function AbsenteeFinder() {
  const { cityId, corridorName } = useParams<{ cityId: string; corridorName: string }>();
  const { data, loading } = useAppData();

  const city = data?.cities.find((c) => c.city_id === cityId);
  const corridor = data?.corridors.find((c) => c.city_id === cityId && c.corridor === corridorName);

  const candidates = useMemo(
    () => (data?.candidates ?? []).filter((c) => c.city_id === cityId && c.corridor === corridorName),
    [data, cityId, corridorName]
  );

  if (loading) return <LoadingState />;
  if (!city || !corridor) return null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-10">
      <Breadcrumb
        items={[
          { label: "Home", to: "/" },
          { label: "City Explorer", to: "/explore" },
          { label: city.city_name, to: `/city/${cityId}` },
          { label: corridor.corridor, to: `/city/${cityId}/corridor/${encodeURIComponent(corridor.corridor)}` },
          { label: "NRI / Absentee Finder" },
        ]}
      />

      <div className="glass mb-6 flex items-start gap-3 rounded-xl p-4 text-sm">
        <Info size={17} className="mt-0.5 shrink-0 text-accent-400" />
        <span className="text-text-lo">
          This is an <strong className="text-text-hi">absentee-likelihood proxy</strong>, staleness-driven,
          not confirmed NRI status. It's thin by design, roughly a 1% ceiling of scanned listings city-wide -
          that reflects what's genuinely detectable in public listing text, not a coverage gap.
        </span>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <motion.div
            layoutId="tile-icon-NRI / Absentee Finder"
            className="rounded-xl bg-accent-500/15 p-3 text-accent-300"
          >
            <ScanSearch size={22} strokeWidth={1.75} />
          </motion.div>
          <div>
            <h1 className="font-display text-2xl font-semibold text-text-hi">NRI / Absentee Finder</h1>
            <p className="mt-1 text-sm text-text-lo">
              {plural(candidates.length, "candidate listing")} in {corridor.corridor}.
            </p>
          </div>
        </div>
        <Link
          to="/directory"
          className="glass-hi flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-text-hi hover:border-accent-500/40"
        >
          <MessagesSquare size={16} className="text-accent-400" />
          NRI Community Directory
        </Link>
      </div>

      <motion.div className="mt-6 space-y-3" initial="hidden" animate="show" variants={candidateContainer}>
        {candidates.map((c) => (
          <motion.div key={c.listing_id} variants={candidateItem} className="glass rounded-xl p-5">
            {!c.traceable && (
              <div
                className="mb-3 flex w-fit items-center gap-1 rounded-full bg-surface-hi px-2.5 py-0.5 text-xs font-medium text-text-faint"
                title="No detail_url was captured for this listing at scrape time - a known scraper gap, not a hidden one."
              >
                <AlertCircle size={11} /> Not traceable, no detail_url
              </div>
            )}
            <PipelineLineage candidate={c} />
          </motion.div>
        ))}
        {candidates.length === 0 && (
          <div className="glass rounded-2xl px-8 py-16 text-center text-sm text-text-lo">
            No candidates flagged in this corridor - consistent with the ~1% detection ceiling, not a bug.
          </div>
        )}
      </motion.div>
    </div>
  );
}
