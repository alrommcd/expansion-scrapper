import { motion } from "framer-motion";
import { ArrowRight, Search } from "lucide-react";
import { useState } from "react";
import { useAppData } from "../data/DataProvider";

interface CitySearchBarProps {
  /** "hero" = the large multi-part Home layout. "pinned" = the compact bar
   * used on the India Network Map screen. Both share layoutId="search-bar"
   * so Framer Motion animates one continuous element between the two
   * screens instead of cross-fading two unrelated ones. */
  variant: "hero" | "pinned";
  onSubmit: (cityId: string) => void;
  initialCityId?: string;
}

/**
 * The one search bar, reused on Home and IndiaNetworkMap via a shared
 * layoutId - per the motion brief, "the search bar is a shared element,
 * not a swap." Must live inside the same <LayoutGroup> as both pages
 * (see App.tsx) for the layoutId to resolve across the route change.
 */
export function CitySearchBar({ variant, onSubmit, initialCityId }: CitySearchBarProps) {
  const { data } = useAppData();
  const [selectedCity, setSelectedCity] = useState(initialCityId ?? "");

  const handleSubmit = () => {
    if (selectedCity) onSubmit(selectedCity);
  };

  if (variant === "pinned") {
    return (
      <motion.div
        layoutId="search-bar"
        className="glass-hi flex items-center gap-2 rounded-xl px-4 py-2.5"
      >
        <Search size={16} className="shrink-0 text-text-faint" />
        <select
          value={selectedCity}
          onChange={(e) => {
            setSelectedCity(e.target.value);
            if (e.target.value) onSubmit(e.target.value);
          }}
          className="w-40 bg-transparent text-sm text-text-hi outline-none [&>option]:bg-surface-hi"
        >
          <option value="">Search a city...</option>
          {data?.cities.map((c) => (
            <option key={c.city_id} value={c.city_id}>
              {c.city_name}
            </option>
          ))}
        </select>
      </motion.div>
    );
  }

  return (
    <motion.div layoutId="search-bar" className="flex flex-col gap-3 sm:flex-row">
      <div className="glass-hi flex flex-1 items-center gap-2 rounded-xl px-4 py-3">
        <Search size={18} className="text-text-faint" />
        <select
          value={selectedCity}
          onChange={(e) => setSelectedCity(e.target.value)}
          className="w-full bg-transparent text-sm text-text-hi outline-none [&>option]:bg-surface-hi"
        >
          <option value="">Search a city...</option>
          {data?.cities.map((c) => (
            <option key={c.city_id} value={c.city_id}>
              {c.city_name}
            </option>
          ))}
        </select>
      </div>
      <button
        onClick={handleSubmit}
        className="flex items-center justify-center gap-2 rounded-xl bg-accent-500 px-6 py-3 text-sm font-medium text-black shadow-lg shadow-accent-900/20 transition-transform hover:scale-[1.02] active:scale-[0.98]"
      >
        Analyze
        <ArrowRight size={16} />
      </button>
    </motion.div>
  );
}
