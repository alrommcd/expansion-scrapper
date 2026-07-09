import { Check, ChevronDown, MapPin } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAppData } from "../data/DataProvider";

/**
 * Persistent, everywhere-in-the-app city switcher. Pune is not this app's home
 * - it is one entry in `data.cities`, currently the only fully-scored one.
 * This is the one place that's allowed to say a city's name outside a data
 * binding, and it says whichever one the URL says, never a hardcoded default.
 */
export function CitySwitcher({ onNavigate }: { onNavigate?: () => void }) {
  const { data } = useAppData();
  const { cityId } = useParams<{ cityId: string }>();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const cities = data?.cities ?? [];
  const current = cities.find((c) => c.city_id === cityId);

  if (cities.length === 0) return null;

  return (
    <div className="relative px-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2.5 rounded-xl border px-3 py-2.5 text-sm text-text-lo transition-colors hover:border-accent-500/40 hover:text-text-hi"
      >
        <MapPin size={16} className="shrink-0 text-accent-400" />
        <span className="min-w-0 flex-1 truncate text-left">
          {current ? current.city_name : `Switch city (${cities.length})`}
        </span>
        <ChevronDown size={14} className={`shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="glass-hi absolute left-3 right-3 top-full z-40 mt-1.5 max-h-72 overflow-y-auto rounded-xl p-1.5">
            {cities.map((c) => (
              <button
                key={c.city_id}
                onClick={() => {
                  setOpen(false);
                  navigate(`/city/${c.city_id}`);
                  onNavigate?.();
                }}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-text-lo transition-colors hover:bg-white/5 hover:text-text-hi"
              >
                <span className="min-w-0 flex-1 truncate">{c.city_name}</span>
                {c.city_id === cityId && <Check size={14} className="shrink-0 text-accent-400" />}
                {!c.has_price_band && (
                  <span className="shrink-0 text-[10px] uppercase tracking-wide text-text-faint">corridors only</span>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
