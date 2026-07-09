import { motion } from "framer-motion";
import { Building2, MapPinned, Users2, MessagesSquare, SearchCode, type LucideIcon } from "lucide-react";
import type { DataShape } from "../data/DataProvider";
import { useSourceInspector, type SourceSpec } from "./SourceInspector";

interface StatDef {
  icon: LucideIcon;
  value: string;
  label: string;
  description: string;
  spec: SourceSpec;
}

function buildStats(data: DataShape): StatDef[] {
  const { stats, brokers, cities, candidates, directory } = data;

  const topBrokers = [...brokers].sort((a, b) => b.broker_activity_score - a.broker_activity_score).slice(0, 6);
  const tracedCandidates = candidates.filter((c) => c.traceable).slice(0, 6);

  return [
    {
      icon: Users2,
      value: stats.total_brokers_indexed.toLocaleString(),
      label: "Brokers indexed",
      description: `Across ${stats.total_corridors_ranked} ranked corridors, all cities`,
      spec: {
        title: "Brokers indexed",
        sourceFile: "output/broker_list_all_cities.csv -> web/public/data/brokers.json",
        summary:
          "Every agent-classified listing poster (dealer/agent/builder prefixes), counted by distinct detail_url per corridor to avoid double-counting one listing twice. Highest-activity rows shown below, each linking to a real listing page.",
        rows: topBrokers.map((b) => ({
          label: `${b.agent_display} - ${b.corridor}, ${b.city_id}`,
          value: `${b.listing_count} listings`,
          href: b.sample_detail_url ?? undefined,
        })),
        moreCount: Math.max(0, brokers.length - topBrokers.length),
      },
    },
    {
      icon: MapPinned,
      value: `${stats.total_cities_fully_scored} / ${stats.total_cities_live}`,
      label: "Cities fully scored",
      description: "Society-fit layer needs a configured price band per city",
      spec: {
        title: "Cities fully scored",
        sourceFile: "config/cities/*.py (product_price_band_min_inr/max_inr) -> web/public/data/cities.json",
        summary:
          "\"Fully scored\" means a city has a business-confirmed product price band, required for the society-fit layer (supply depth, resale velocity, price consistency). Corridor ranking and Broker Finder don't need one and run for every city.",
        rows: cities.map((c) => ({
          label: c.city_name,
          value: c.has_price_band ? "has price band" : "no price band configured",
        })),
      },
    },
    {
      icon: Building2,
      value: stats.total_absentee_candidates.toLocaleString(),
      label: "Absentee candidates flagged",
      description: "Likelihood proxy, staleness-driven - not confirmed NRI status",
      spec: {
        title: "Absentee candidates flagged",
        sourceFile: "output/absentee_candidates_all_cities.csv -> web/public/data/absentee_candidates.json",
        summary:
          "Canonical (deduped) listings matching one of two validated signals: a distinctive-name owner posting 2+ properties, or genuine \"never occupied\" language. A likelihood proxy, never confirmed NRI/identity. Traceable rows shown below link to the real listing.",
        rows: tracedCandidates.map((c) => ({
          label: `${c.society ?? "society unavailable"} - ${c.corridor}, ${c.city_id} (${c.signal_matched})`,
          value: `score ${c.score}`,
          href: c.detail_url ?? undefined,
        })),
        moreCount: Math.max(0, candidates.length - tracedCandidates.length),
      },
    },
    {
      icon: MessagesSquare,
      value: stats.total_directory_links.toLocaleString(),
      label: "Directory links catalogued",
      description: "Manual outreach directory, needs human vetting before use",
      spec: {
        title: "Directory links catalogued",
        sourceFile: "output/nri_community_directory.csv -> web/public/data/nri_directory.json",
        summary:
          "Public WhatsApp/Facebook group links from link-aggregator sites, deduplicated by link URL. Not scraped from WhatsApp/Facebook itself. Names aren't always reliably tied to the link they're attached to - vet before use.",
        rows: directory.slice(0, 6).map((d) => ({
          label: `${d.group_name} (${d.platform})`,
          value: d.city_focus || "no city tag",
          href: d.link,
        })),
        moreCount: Math.max(0, directory.length - 6),
      },
    },
  ];
}

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const } },
};

export function StatRow({ data }: { data: DataShape }) {
  const items = buildStats(data);
  const openSource = useSourceInspector();

  return (
    <motion.div
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-60px" }}
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
    >
      {items.map((s) => (
        <motion.button
          key={s.label}
          variants={item}
          onClick={() => openSource(s.spec)}
          className="group glass rounded-2xl p-5 text-left transition-colors hover:border-accent-500/40"
        >
          <div className="mb-4 flex items-start justify-between">
            <div className="inline-flex rounded-xl bg-accent-500/15 p-2.5 text-accent-300">
              <s.icon size={20} strokeWidth={1.75} />
            </div>
            <SearchCode
              size={15}
              className="text-text-faint opacity-0 transition-opacity group-hover:opacity-100"
            />
          </div>
          <div className="font-mono text-3xl font-semibold tabular text-text-hi">{s.value}</div>
          <div className="mt-1 text-sm font-medium text-text-hi">{s.label}</div>
          <div className="mt-1 text-xs leading-relaxed text-text-lo">{s.description}</div>
        </motion.button>
      ))}
    </motion.div>
  );
}
