import { motion, useReducedMotion } from "framer-motion";
import { MapPin } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CitySearchBar } from "../components/CitySearchBar";
import { LoadingState } from "../components/LoadingState";
import { useAppData } from "../data/DataProvider";

const VIEWBOX_W = 400;
const VIEWBOX_H = 520;

// Approximate, stylized positions within the viewBox - illustrative
// dot-matrix art, not surveyed cartography. Only the 5 registered cities
// get real nodes; nothing here is a claim of geographic precision.
const CITY_POSITIONS: Record<string, { x: number; y: number }> = {
  mumbai: { x: 95, y: 275 },
  pune: { x: 128, y: 300 },
  hyderabad: { x: 195, y: 320 },
  bangalore: { x: 168, y: 388 },
  chennai: { x: 232, y: 400 },
};

// A small set of nearest-neighbor connections for the "network" line look -
// hand-picked, not computed, since there are only 5 nodes.
const CONNECTIONS: [string, string][] = [
  ["mumbai", "pune"],
  ["pune", "hyderabad"],
  ["hyderabad", "bangalore"],
  ["hyderabad", "chennai"],
  ["bangalore", "chennai"],
];

// Stylized silhouette (hand-authored approximation, not a licensed map
// asset) - a dense dot-matrix pattern is clipped to this path via SVG
// clipPath, giving the "satellite heat-map" look without per-dot React
// rendering (a <rect> + <pattern> instead of ~1000 individual <circle>s).
const INDIA_PATH =
  "M150,15 L178,8 L200,30 L222,50 L248,58 L268,88 L284,128 L292,168 L280,192 L284,228 " +
  "L272,268 L258,288 L262,326 L248,368 L232,408 L212,438 L196,464 L182,478 L172,458 " +
  "L158,428 L142,398 L126,378 L112,348 L96,328 L92,298 L76,268 L66,230 L60,190 L66,150 " +
  "L82,110 L98,80 L112,54 L126,34 Z";

function nodePercent(pos: { x: number; y: number }) {
  return { left: `${(pos.x / VIEWBOX_W) * 100}%`, top: `${(pos.y / VIEWBOX_H) * 100}%` };
}

export function IndiaNetworkMap() {
  const { data, loading } = useAppData();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const reduceMotion = useReducedMotion();
  const highlightedId = params.get("city");
  // Set the instant a node/CTA is clicked; everything except the target
  // node blurs and fades (the "focus pull" the motion brief asks for) while
  // navigation is held for one beat so the effect is actually visible
  // before the route unmounts this page. Skipped entirely under reduced
  // motion - a direct navigate() instead, no blur/scale transition at all.
  const [focusingOn, setFocusingOn] = useState<string | null>(null);

  const openCity = (cityId: string) => {
    if (reduceMotion) {
      navigate(`/city/${cityId}`);
      return;
    }
    setFocusingOn(cityId);
    setTimeout(() => navigate(`/city/${cityId}`), 550);
  };

  if (loading) return <LoadingState />;

  const cities = data?.cities.filter((c) => CITY_POSITIONS[c.city_id]) ?? [];
  const highlighted = cities.find((c) => c.city_id === highlightedId);
  const others = cities.filter((c) => c.city_id !== highlightedId);
  // Highlighted city renders last so it's on top and its pulse reads as the
  // "arrival" - the loose stagger the brief asks for, not a simultaneous
  // reveal of all 5 at once.
  const orderedCities = highlighted ? [...others, highlighted] : cities;

  return (
    <div className="relative min-h-screen overflow-hidden">
      <motion.div
        className="sticky top-0 z-20 flex justify-center px-4 pt-6 sm:px-6 lg:px-10"
        animate={{ opacity: focusingOn ? 0 : 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="w-full max-w-md">
          <CitySearchBar
            variant="pinned"
            initialCityId={highlightedId ?? undefined}
            onSubmit={(cityId) => navigate(`/explore-map?city=${cityId}`)}
          />
        </div>
      </motion.div>

      <div className="relative mx-auto mt-6 aspect-[400/520] w-full max-w-2xl px-6">
        <motion.svg
          viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
          className="h-full w-full"
          aria-hidden="true"
          animate={{ opacity: focusingOn ? 0.1 : 1, filter: focusingOn ? "blur(5px)" : "blur(0px)" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <defs>
            <pattern id="india-dot-grid" width="9" height="9" patternUnits="userSpaceOnUse">
              <circle cx="1.1" cy="1.1" r="1.1" fill="var(--color-accent-400)" opacity="0.55" />
            </pattern>
            <clipPath id="india-silhouette">
              <path d={INDIA_PATH} />
            </clipPath>
          </defs>

          <motion.rect
            x="0"
            y="0"
            width={VIEWBOX_W}
            height={VIEWBOX_H}
            fill="url(#india-dot-grid)"
            clipPath="url(#india-silhouette)"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: reduceMotion ? 0.15 : 0.7, ease: [0.16, 1, 0.3, 1] }}
          />

          {CONNECTIONS.map(([a, b]) => {
            const pa = CITY_POSITIONS[a];
            const pb = CITY_POSITIONS[b];
            return (
              <motion.line
                key={`${a}-${b}`}
                x1={pa.x}
                y1={pa.y}
                x2={pb.x}
                y2={pb.y}
                stroke="var(--color-accent-400)"
                strokeWidth="0.75"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.35 }}
                transition={{ duration: reduceMotion ? 0.15 : 0.6, delay: reduceMotion ? 0 : 0.4 }}
              />
            );
          })}
        </motion.svg>

        {/* City nodes as HTML overlays (not SVG) so each can carry a real
            <Link>-style click target and a text label without foreignObject
            quirks - positioned by percentage to match the SVG viewBox. */}
        {orderedCities.map((city, i) => {
          const pos = CITY_POSITIONS[city.city_id];
          const isHighlighted = city.city_id === highlightedId;
          const isFocusTarget = focusingOn === city.city_id;
          const isBlurredOut = focusingOn !== null && !isFocusTarget;
          return (
            <motion.button
              key={city.city_id}
              onClick={() => openCity(city.city_id)}
              className="group absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer"
              style={nodePercent(pos)}
              initial={{ opacity: 0, scale: 0.4 }}
              animate={
                isFocusTarget
                  ? { opacity: 1, scale: 2.4, filter: "blur(0px)" }
                  : isBlurredOut
                    ? { opacity: 0, scale: 1, filter: "blur(5px)" }
                    : { opacity: 1, scale: 1, filter: "blur(0px)" }
              }
              transition={
                isFocusTarget || isBlurredOut
                  ? { duration: 0.5, ease: [0.16, 1, 0.3, 1] }
                  : {
                      duration: reduceMotion ? 0.15 : 0.5,
                      delay: reduceMotion ? 0 : 0.5 + i * 0.12,
                      ease: [0.16, 1, 0.3, 1],
                    }
              }
            >
              <span className="relative flex items-center justify-center">
                {isHighlighted && (
                  <motion.span
                    className="absolute h-8 w-8 rounded-full bg-accent-bright/25"
                    initial={{ scale: 0.6, opacity: 0.7 }}
                    animate={reduceMotion ? { opacity: 0.3 } : { scale: [0.6, 1.6], opacity: [0.7, 0] }}
                    transition={{ duration: 0.9, delay: 0.5 + (orderedCities.length - 1) * 0.12 + 0.2 }}
                  />
                )}
                <span
                  className={`block rounded-full transition-transform group-hover:scale-125 ${
                    isHighlighted ? "h-3.5 w-3.5 bg-accent-bright" : "h-2 w-2 bg-accent-500"
                  }`}
                />
              </span>
              <motion.span
                layoutId={isHighlighted ? `crumb-${city.city_name}` : undefined}
                className={`pointer-events-none absolute left-1/2 top-full mt-2 flex -translate-x-1/2 items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium backdrop-blur-sm ${
                  isHighlighted ? "bg-void/80 text-text-hi" : "bg-void/50 text-text-lo"
                }`}
                initial={isHighlighted ? { opacity: 0 } : false}
                animate={{ opacity: 1 }}
                transition={{ delay: isHighlighted ? 0.5 + (orderedCities.length - 1) * 0.12 + 0.15 : 0 }}
              >
                {isHighlighted && <MapPin size={11} />}
                {city.city_name}
              </motion.span>
            </motion.button>
          );
        })}
      </div>

      {highlighted && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: focusingOn ? 0 : 1, y: 0 }}
          transition={{ delay: focusingOn ? 0 : 0.5 + (orderedCities.length - 1) * 0.12 + 0.3, duration: 0.4 }}
          className="mx-auto mt-8 flex max-w-md justify-center px-6 pb-10"
        >
          <button
            onClick={() => openCity(highlighted.city_id)}
            className="flex items-center gap-2 rounded-xl bg-accent-500 px-6 py-3 text-sm font-medium text-black shadow-lg shadow-accent-900/20 transition-transform hover:scale-[1.02] active:scale-[0.98]"
          >
            Open {highlighted.city_name}
          </button>
        </motion.div>
      )}
    </div>
  );
}
