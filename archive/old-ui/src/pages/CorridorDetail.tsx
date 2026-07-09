import { motion } from "framer-motion";
import { ArrowRight, Building2, ScanSearch, Users } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { Breadcrumb } from "../components/Breadcrumb";
import { ImageTile } from "../components/ImageTile";
import { LoadingState } from "../components/LoadingState";
import { ScoreRing } from "../components/ScoreRing";
import { useAppData } from "../data/DataProvider";
import { plural } from "../lib/format";
import { corridorKey } from "../lib/images";

export function CorridorDetail() {
  const { cityId, corridorName } = useParams<{ cityId: string; corridorName: string }>();
  const { data, loading } = useAppData();

  const city = data?.cities.find((c) => c.city_id === cityId);
  const corridor = data?.corridors.find((c) => c.city_id === cityId && c.corridor === corridorName);
  const societyCount = data?.societies.filter((s) => s.city_id === cityId && s.corridor === corridorName).length ?? 0;
  const brokerCount = data?.brokers.filter((b) => b.city_id === cityId && b.corridor === corridorName).length ?? 0;
  const candidateCount =
    data?.candidates.filter((c) => c.city_id === cityId && c.corridor === corridorName).length ?? 0;

  if (loading) return <LoadingState />;
  if (!city || !corridor) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-16 text-center text-text-lo">
        Corridor not found. <Link to="/explore" className="text-accent-400 hover:underline">Back to City Explorer</Link>
      </div>
    );
  }

  const tiles = [
    {
      to: `/city/${cityId}/corridor/${encodeURIComponent(corridor.corridor)}/society`,
      icon: Building2,
      title: "Society Finder",
      desc: city.has_price_band
        ? `${plural(societyCount, "society", "societies")} scored on supply, velocity, consistency, and rating`
        : "Not scored yet, no product price band configured for this city",
      ringKind: "society" as const,
      count: societyCount,
      available: city.has_price_band,
    },
    {
      to: `/city/${cityId}/corridor/${encodeURIComponent(corridor.corridor)}/broker`,
      icon: Users,
      title: "Broker Finder",
      desc: `${plural(brokerCount, "agent")} active in this corridor - an activity list, not a contact list`,
      ringKind: "broker" as const,
      count: brokerCount,
      available: true,
    },
    {
      to: `/city/${cityId}/corridor/${encodeURIComponent(corridor.corridor)}/absentee`,
      icon: ScanSearch,
      title: "NRI / Absentee Finder",
      desc: `${plural(candidateCount, "candidate listing")} - likelihood proxy, not confirmed NRI status`,
      ringKind: null,
      count: candidateCount,
      available: true,
    },
  ];

  const tileContainer = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } };
  const tileItem = {
    hidden: { opacity: 0, y: 18 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const } },
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-10">
      <Breadcrumb
        items={[
          { label: "Home", to: "/" },
          { label: "City Explorer", to: "/explore" },
          { label: city.city_name, to: `/city/${cityId}` },
          { label: corridor.corridor },
        ]}
      />

      <div className="glass relative overflow-hidden rounded-2xl">
        <div className="absolute inset-0">
          <ImageTile
            name={corridor.corridor}
            bucket="corridors"
            manifestKey={corridorKey(city.city_name, corridor.corridor)}
            className="h-full w-full opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-surface via-surface/70 to-transparent" />
        </div>
        <div className="relative flex flex-wrap items-center justify-between gap-6 p-6">
          <div>
            <h1 className="font-display text-2xl font-semibold text-text-hi">{corridor.corridor}</h1>
            <p className="mt-1 text-sm text-text-lo">{city.city_name}</p>
          </div>
          <ScoreRing
            kind="corridor"
            value={corridor.fit_score}
            unavailableReason={`Failed: ${corridor.failed_gates.join(", ")}`}
          />
        </div>
      </div>

      <motion.div
        className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-3"
        initial="hidden"
        animate="show"
        variants={tileContainer}
      >
        {tiles.map((tile) => (
          <motion.div key={tile.title} variants={tileItem}>
            <Link
              to={tile.to}
              className="glass group flex h-full flex-col gap-4 rounded-2xl p-6 transition-all hover:-translate-y-1 hover:border-accent-500/40 hover:shadow-xl hover:shadow-accent-900/40"
            >
              <div className="flex items-center justify-between">
                <motion.div layoutId={`tile-icon-${tile.title}`} className="rounded-xl bg-accent-500/15 p-3 text-accent-300">
                  <tile.icon size={22} strokeWidth={1.75} />
                </motion.div>
                {!tile.available && (
                  <span className="rounded-full bg-surface-hi px-2.5 py-1 text-[11px] font-medium text-text-faint">
                    Not scored
                  </span>
                )}
              </div>
              <div>
                <div className="font-display text-lg font-medium text-text-hi">{tile.title}</div>
                <p className="mt-1.5 text-sm leading-relaxed text-text-lo">{tile.desc}</p>
              </div>
              <div className="mt-auto flex items-center gap-1 text-sm text-accent-400 opacity-0 transition-opacity group-hover:opacity-100">
                Open <ArrowRight size={14} />
              </div>
            </Link>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
