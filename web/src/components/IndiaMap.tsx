import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { SelectionMetrics } from "./SelectionMetrics";

const VIEWBOX_W = 400;
const VIEWBOX_H = 358;

// cities.json (read directly before building this - confirmed) has no
// lat/long field: city_id, city_name, state, corridor_count, has_price_band
// only. These positions are NOT derived from that file. The prior version of
// this map reused a hand-authored polygon from an older, unrelated build
// (archive/old-ui) that turned out to be a poor approximation - no
// northeast extension, a rounded blob instead of the real peninsula taper -
// caught by direct comparison against the project's own india.png reference.
// Replaced with an outline traced from that same reference image (Gaussian
// blur to merge its dot-matrix texture into a solid silhouette, largest-
// connected-component + hole-fill to drop stray decorative nodes and the
// city-label cutouts, marching-squares contour, Douglas-Peucker simplified
// to 99 points - see extract_india_outline.py/trace_and_markers.py/
// build_final_path.py/refit_viewbox.py in this session's scratch history).
// Still hand-derived from a stylized reference image, not surveyed
// cartography, but now actually recognizable as India, including the
// northeast. Viewbox is 400x358 (the traced shape's own bounding-box aspect
// ratio, ~1.21:1), not the prior 400x520 - that portrait ratio was inherited
// from the old hand-drawn path and left ~40% of the box empty above/below
// the new, wider-than-tall traced shape, which silently capped how big the
// map could ever look regardless of its container's size. City positions
// below were located the same way, from the reference image's own 5 marker
// dots (identified as the only blobs with a consistent ~90px size, distinct
// from surrounding label-text glyphs), mapped through the same coordinate
// transform as the outline so both line up.
const CITY_POSITIONS: Record<string, { x: number; y: number }> = {
  mumbai: { x: 68.9, y: 177.8 },
  pune: { x: 93.1, y: 202.6 },
  hyderabad: { x: 151.1, y: 217.0 },
  bangalore: { x: 116.9, y: 262.3 },
  chennai: { x: 178.2, y: 267.8 },
};

const INDIA_PATH =
  "M135.4,320.5 L126.0,318.8 L116.4,311.5 L109.9,301.4 L104.3,286.4 L90.6,269.4 L83.1,249.6 " +
  "L69.4,226.7 L62.6,193.2 L55.7,177.5 L53.6,175.7 L42.2,176.0 L34.4,172.1 L22.2,158.9 " +
  "L20.2,149.8 L14.0,138.1 L15.3,132.5 L21.3,126.8 L42.7,123.1 L35.2,105.5 L38.9,96.2 " +
  "L49.0,89.3 L65.0,89.3 L78.2,78.4 L87.4,66.3 L87.7,62.4 L81.5,51.0 L82.5,38.9 L78.2,32.4 " +
  "L78.2,26.2 L81.7,21.5 L93.4,16.0 L108.1,14.0 L134.5,27.7 L147.5,25.1 L159.9,27.4 " +
  "L165.3,31.8 L166.9,36.0 L166.6,42.9 L160.1,53.6 L161.4,64.4 L159.7,70.2 L161.5,73.3 " +
  "L177.2,78.9 L192.5,89.0 L241.7,100.7 L255.4,100.7 L260.8,91.8 L267.8,87.4 L275.3,89.0 " +
  "L285.4,96.8 L302.0,95.2 L304.2,86.9 L306.9,83.8 L338.2,68.4 L357.5,64.5 L365.6,65.5 " +
  "L384.4,79.4 L386.0,84.9 L383.4,92.7 L379.6,96.8 L364.2,104.5 L351.4,127.9 L343.3,137.4 " +
  "L339.4,150.4 L334.3,155.5 L326.8,155.5 L319.3,149.0 L309.5,145.7 L303.5,138.1 " +
  "L302.0,127.1 L284.4,125.2 L283.0,130.2 L284.6,137.7 L291.1,154.4 L288.5,162.5 " +
  "L279.2,167.2 L268.5,166.3 L263.2,167.9 L254.8,183.2 L240.1,189.4 L217.4,210.4 " +
  "L211.4,220.7 L187.9,233.1 L183.9,237.2 L184.8,254.1 L189.2,256.6 L209.8,256.6 " +
  "L217.9,258.5 L224.0,265.9 L221.0,276.0 L213.4,279.7 L179.8,281.0 L173.3,291.1 " +
  "L165.1,295.4 L158.6,303.8 L149.5,309.1 L143.3,316.9 L135.4,320.5 Z";

interface City {
  city_id: string;
  city_name: string;
  state: string;
  corridor_count: number;
  has_price_band: boolean;
}

function nodePosition(pos: { x: number; y: number }) {
  return { left: `${(pos.x / VIEWBOX_W) * 100}%`, top: `${(pos.y / VIEWBOX_H) * 100}%` };
}

interface IndiaMapProps {
  onSelectCity: (cityId: string) => void;
}

export function IndiaMap({ onSelectCity }: IndiaMapProps) {
  const [cities, setCities] = useState<City[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  useEffect(() => {
    fetch("/data/cities.json")
      .then((res) => res.json())
      .then((data: City[]) => setCities(data.filter((c) => CITY_POSITIONS[c.city_id])));
  }, []);

  return (
    <div className="relative flex h-screen w-full items-center justify-center overflow-hidden bg-black p-2">
      <SelectionMetrics />
      {/*
        Sized off height+aspect-ratio with a max-width clamp, not a fixed
        max-width - so whichever dimension is tighter (viewport height on
        wide/landscape screens, viewport width on narrow/portrait ones)
        is what limits it, and it always scales to fill nearly the whole
        screen without ever clipping or distorting the shape. Bumped from
        92vh/92vw per explicit "zoom in further" request - path/marker data
        itself is untouched, this is purely a container-size change so the
        whole composition scales up uniformly together.
      */}
      <div className="relative aspect-[400/358] h-[98vh] max-w-[97vw]">
        <svg viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`} className="h-full w-full" aria-hidden="true">
          <defs>
            <pattern id="india-dot-grid" width="9" height="9" patternUnits="userSpaceOnUse">
              <circle cx="1.1" cy="1.1" r="1.1" fill="#a3e635" opacity="0.5" />
            </pattern>
            <clipPath id="india-silhouette">
              <path d={INDIA_PATH} />
            </clipPath>
          </defs>
          <rect
            x="0"
            y="0"
            width={VIEWBOX_W}
            height={VIEWBOX_H}
            fill="url(#india-dot-grid)"
            clipPath="url(#india-silhouette)"
          />
        </svg>

        {/* HTML overlays (not SVG) so each marker is a real button with a
            text label, positioned by percentage to match the SVG viewBox.
            All 5 render with identical styling - no city is featured. */}
        {cities.map((city) => {
          const pos = CITY_POSITIONS[city.city_id];
          const isHovered = hoveredId === city.city_id;
          return (
            <button
              key={city.city_id}
              type="button"
              onMouseEnter={() => setHoveredId(city.city_id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => onSelectCity(city.city_id)}
              className="group absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer"
              style={nodePosition(pos)}
            >
              <span className="relative flex h-5 w-5 items-center justify-center">
                {isHovered && (
                  <motion.span
                    className="absolute h-5 w-5 rounded-full bg-lime-400/25"
                    initial={{ scale: 0.7, opacity: 0.7 }}
                    animate={{ scale: 1.8, opacity: 0 }}
                    transition={{ duration: 0.7, repeat: Infinity, ease: "easeOut" }}
                  />
                )}
                <span
                  className={`block rounded-full bg-lime-400 transition-transform duration-200 ${
                    isHovered ? "scale-150" : "scale-100"
                  }`}
                  style={{ width: 8, height: 8 }}
                />
              </span>
              <span
                className={`pointer-events-none absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap rounded-sm border px-1 py-0.5 text-[9px] font-medium backdrop-blur-sm transition-colors duration-200 sm:mt-2 sm:px-2.5 sm:py-1 sm:text-xs ${
                  isHovered ? "border-lime-400/50 bg-black/70 text-white" : "border-white/20 bg-black/50 text-white/70"
                }`}
              >
                {city.city_name}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
