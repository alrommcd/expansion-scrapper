import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import { Breadcrumb } from "../components/Breadcrumb";
import { ImageTile } from "../components/ImageTile";
import { LoadingState } from "../components/LoadingState";
import { useAppData } from "../data/DataProvider";
import { plural } from "../lib/format";

export function CityExplorer() {
  const { data, loading } = useAppData();

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-10">
      <Breadcrumb items={[{ label: "Home", to: "/" }, { label: "City Explorer" }]} />
      <h1 className="font-display text-2xl font-semibold text-text-hi">City Explorer</h1>
      <p className="mt-1 text-sm text-text-lo">
        Every city registered in the engine. Corridor and broker data is available for all of
        them; the society-fit layer needs a configured product price band per city.
      </p>

      {loading && <LoadingState />}

      <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {data?.cities.map((city, i) => (
          <motion.div
            key={city.city_id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            <Link
              to={`/city/${city.city_id}`}
              className="glass group flex flex-col overflow-hidden rounded-2xl transition-all hover:-translate-y-1 hover:border-accent-500/40 hover:shadow-xl hover:shadow-accent-900/40"
            >
              <ImageTile
                name={city.city_name}
                bucket="cities"
                manifestKey={city.city_name}
                className="h-32 w-full"
                showIllustrativeTag
              />
              <div className="flex flex-1 flex-col p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-display text-lg font-medium text-text-hi">{city.city_name}</div>
                    <div className="flex items-center gap-1 text-xs text-text-lo">
                      <MapPin size={12} />
                      {city.state}
                    </div>
                  </div>
                  {city.has_price_band ? (
                    <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                      <CheckCircle2 size={12} /> Fully scored
                    </span>
                  ) : (
                    <span className="rounded-full bg-surface-hi px-2.5 py-1 text-[11px] font-medium text-text-lo">
                      Corridors + brokers only
                    </span>
                  )}
                </div>
                <div className="mt-4 flex items-center justify-between text-sm">
                  <span className="text-text-lo">{plural(city.corridor_count, "corridor")} tracked</span>
                  <span className="flex items-center gap-1 text-accent-400 opacity-0 transition-opacity group-hover:opacity-100">
                    Explore <ArrowRight size={14} />
                  </span>
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
