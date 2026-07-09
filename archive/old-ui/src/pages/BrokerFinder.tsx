import { motion } from "framer-motion";
import { ArrowUpDown, ExternalLink, Globe, Info, MapPin, Phone, Search, Users } from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Breadcrumb } from "../components/Breadcrumb";
import { LoadingState } from "../components/LoadingState";
import { ScoreRing } from "../components/ScoreRing";
import { useSourceInspector } from "../components/SourceInspector";
import { useAppData } from "../data/DataProvider";
import { plural } from "../lib/format";

const PHONE_REASON = "MagicBricks gates phone behind a \"Get Phone No.\" click-through - never rendered as text, so it can't be scraped.";
const COMPANY_REASON = "The site doesn't separate a person's name from an agency's name into two fields - this text is exactly what was published.";

// No entrance animation existed on these rows before this pass - added
// fresh, same staggerChildren/delayChildren pattern as the rest of the app
// (not the manual per-index delay the corridor/society pages used to have).
const rowContainer = { hidden: {}, show: { transition: { staggerChildren: 0.03 } } };
const rowItem = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const } },
};

export function BrokerFinder() {
  const { cityId, corridorName } = useParams<{ cityId: string; corridorName: string }>();
  const { data, loading } = useAppData();
  const [query, setQuery] = useState("");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);
  const openSource = useSourceInspector();

  const city = data?.cities.find((c) => c.city_id === cityId);
  const corridor = data?.corridors.find((c) => c.city_id === cityId && c.corridor === corridorName);

  const brokers = useMemo(() => {
    let rows = (data?.brokers ?? []).filter((b) => b.city_id === cityId && b.corridor === corridorName);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      rows = rows.filter((b) => b.agent_display.toLowerCase().includes(q));
    }
    return [...rows].sort((a, b) => (a.broker_activity_score - b.broker_activity_score) * sortDir);
  }, [data, cityId, corridorName, query, sortDir]);

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
          { label: "Broker Finder" },
        ]}
      />

      <div className="glass mb-6 flex items-start gap-3 rounded-xl p-4 text-sm">
        <Info size={17} className="mt-0.5 shrink-0 text-accent-400" />
        <span className="text-text-lo">
          This is an <strong className="text-text-hi">activity list</strong>, not a contact list. It ranks
          agents by how many distinct listings they posted in this corridor - MagicBricks itself never
          confirms phone numbers or company names. The "Verified contact" column is a separate enrichment
          step against Google Places only, confidence-gated - it shows "Unavailable" rather than a guess
          wherever no confident business match was found.
        </span>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <motion.div layoutId="tile-icon-Broker Finder" className="rounded-xl bg-accent-500/15 p-3 text-accent-300">
            <Users size={22} strokeWidth={1.75} />
          </motion.div>
          <div>
            <h1 className="font-display text-2xl font-semibold text-text-hi">Broker Finder</h1>
            <p className="mt-1 text-sm text-text-lo">
              {plural(brokers.length, "agent")} active in {corridor.corridor}, ranked by broker_activity_score
              (percentile rank of listing count within {city.city_name}).
            </p>
          </div>
        </div>
        <div className="glass-hi flex items-center gap-2 rounded-xl px-3 py-2">
          <Search size={16} className="text-text-faint" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter agents..."
            className="w-48 bg-transparent text-sm text-text-hi outline-none placeholder:text-text-faint"
          />
        </div>
      </div>

      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[920px] border-separate border-spacing-y-2">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-text-faint">
              <th className="px-4 py-2 font-medium">Agent</th>
              <th className="px-4 py-2 font-medium">Company</th>
              <th className="px-4 py-2 font-medium">Phone</th>
              <th className="px-4 py-2 font-medium">
                <button onClick={() => setSortDir((d) => (d === 1 ? -1 : 1))} className="flex items-center gap-1 hover:text-text-lo">
                  Listings <ArrowUpDown size={12} />
                </button>
              </th>
              <th className="px-4 py-2 font-medium">Activity</th>
              <th className="px-4 py-2 font-medium">Verified contact</th>
              <th className="px-4 py-2 font-medium">Source</th>
            </tr>
          </thead>
          <motion.tbody initial="hidden" animate="show" variants={rowContainer}>
            {brokers.map((b) => (
              <motion.tr
                key={b.agent_normalized}
                variants={rowItem}
                className="glass rounded-xl text-sm [&>td:first-child]:rounded-l-xl [&>td:last-child]:rounded-r-xl"
              >
                <td className="px-4 py-3 font-medium text-text-hi">{b.agent_display}</td>
                <td className="px-4 py-3 text-text-faint" title={COMPANY_REASON}>
                  {b.company ?? "unavailable via source"}
                </td>
                <td className="px-4 py-3 text-text-faint" title={PHONE_REASON}>
                  {b.phone ?? "unavailable via source"}
                </td>
                <td className="px-4 py-3 font-mono tabular text-text-hi">{b.listing_count}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() =>
                      openSource({
                        title: `${b.agent_display} - broker_activity_score`,
                        sourceFile: "scoring/broker_list.py -> output/broker_list_all_cities.csv -> web/public/data/brokers.json",
                        summary:
                          "Percentile rank of distinct-listing count within this city, all corridors. Counts distinct detail_url per agent to avoid double-counting a repeat-listed property. An activity list, not a contact list or a deal-quality signal.",
                        rows: [
                          { label: "Distinct listings counted", value: `${b.listing_count}` },
                          { label: "Corridor", value: b.corridor },
                          { label: "Phone (from listing)", value: b.phone ?? "unavailable via source (site gates it)" },
                          { label: "Company (from listing)", value: b.company ?? "unavailable via source (not a separate field)" },
                          {
                            label: "Verified contact",
                            value: b.contact_available
                              ? `${b.contact_phone ?? b.contact_website ?? b.contact_address} (${b.contact_source})`
                              : "unavailable, no confident Places match",
                          },
                          ...(b.sample_detail_url ? [{ label: "Sample listing", value: "open listing", href: b.sample_detail_url }] : []),
                        ],
                      })
                    }
                    className="rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500"
                    aria-label={`Inspect source for ${b.agent_display}'s activity score`}
                  >
                    <ScoreRing kind="broker" value={b.broker_activity_score} size={48} showLabel={false} />
                  </button>
                </td>
                <td className="px-4 py-3">
                  {b.contact_available ? (
                    <div className="space-y-1 text-xs">
                      {b.contact_phone && (
                        <div className="flex items-center gap-1.5 text-text-hi">
                          <Phone size={11} className="shrink-0 text-emerald-400" /> {b.contact_phone}
                        </div>
                      )}
                      {b.contact_website && (
                        <a
                          href={b.contact_website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 text-accent-400 hover:underline"
                        >
                          <Globe size={11} className="shrink-0" /> Website
                        </a>
                      )}
                      {b.contact_address && !b.contact_phone && !b.contact_website && (
                        <div className="flex items-center gap-1.5 text-text-lo">
                          <MapPin size={11} className="shrink-0" /> {b.contact_address}
                        </div>
                      )}
                      <div className="text-[10px] text-text-faint">sourced from {b.contact_source}</div>
                    </div>
                  ) : (
                    <span className="text-xs text-text-faint" title={b.contact_confidence_note ?? undefined}>
                      Unavailable
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {b.sample_detail_url ? (
                    <a
                      href={b.sample_detail_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-accent-400 hover:underline"
                    >
                      Listing <ExternalLink size={12} />
                    </a>
                  ) : (
                    <span className="text-text-faint">unavailable</span>
                  )}
                </td>
              </motion.tr>
            ))}
          </motion.tbody>
        </table>
        {brokers.length === 0 && <div className="py-12 text-center text-sm text-text-lo">No brokers match.</div>}
      </div>
    </div>
  );
}
