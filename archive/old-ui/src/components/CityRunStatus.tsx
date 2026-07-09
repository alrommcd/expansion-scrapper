import { motion } from "framer-motion";
import { ArrowUpRight, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import type { DataShape } from "../data/DataProvider";
import { ImageTile } from "./ImageTile";

/**
 * Stands in for a "recent projects" row - this product has no project
 * concept in its data, only cities the pipeline has actually been run
 * against. Rather than invent project rows to match the reference layout,
 * this shows each city's real run status: corridors tracked, brokers
 * indexed, candidates flagged, and whether the society-fit layer is fully
 * scored - the same fields already shipped elsewhere, just city-scoped here.
 */
export function CityRunStatus({ data }: { data: DataShape }) {
  const rows = data.cities.map((c) => ({
    city: c,
    brokers: data.brokers.filter((b) => b.city_id === c.city_id).length,
    candidates: data.candidates.filter((cd) => cd.city_id === c.city_id).length,
  }));

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      {rows.map((r, i) => (
        <motion.div
          key={r.city.city_id}
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ delay: i * 0.06, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <Link
            to={`/city/${r.city.city_id}`}
            className="glass group flex flex-col overflow-hidden rounded-2xl transition-all hover:-translate-y-1 hover:border-accent-500/40 hover:shadow-xl hover:shadow-accent-900/40"
          >
            <ImageTile
              name={r.city.city_name}
              bucket="cities"
              manifestKey={r.city.city_name}
              className="h-24 w-full"
              showIllustrativeTag
            />
            <div className="flex flex-1 flex-col gap-2 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="font-display text-sm font-medium text-text-hi">{r.city.city_name}</span>
                {r.city.has_price_band ? (
                  <CheckCircle2 size={14} className="shrink-0 text-emerald-400" />
                ) : (
                  <ArrowUpRight size={14} className="shrink-0 text-text-faint opacity-0 group-hover:opacity-100" />
                )}
              </div>
              <div className="space-y-1 font-mono text-[11px] tabular text-text-lo">
                <div>{r.city.corridor_count} corridors tracked</div>
                <div>{r.brokers.toLocaleString()} brokers indexed</div>
                <div>{r.candidates} candidates flagged</div>
              </div>
              <div className="mt-auto pt-1 text-[11px] text-text-faint">
                {r.city.has_price_band ? "Society-fit fully scored" : "Corridors + brokers only"}
              </div>
            </div>
          </Link>
        </motion.div>
      ))}
    </div>
  );
}
