import { Canvas } from "@react-three/fiber";
import { AnimatePresence, motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CorridorDetail } from "./components/CorridorDetail";
import { CorridorList } from "./components/CorridorList";
import { HeroSphere } from "./components/HeroSphere";
import { IndiaMap } from "./components/IndiaMap";
import { ParticleOverlay } from "./components/ParticleField";

// Abstract network/intelligence mark - three outer nodes plus a central hub,
// deliberately not a globe (the hero sphere already owns that shape).
function NetworkMark() {
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" fill="none" aria-hidden className="text-lime-400">
      <g stroke="currentColor" strokeWidth="1.2" strokeOpacity="0.55">
        <line x1="16" y1="6" x2="6" y2="24" />
        <line x1="16" y1="6" x2="26" y2="24" />
        <line x1="6" y1="24" x2="26" y2="24" />
        <line x1="16" y1="6" x2="16" y2="18" />
        <line x1="6" y1="24" x2="16" y2="18" />
        <line x1="26" y1="24" x2="16" y2="18" />
      </g>
      <circle cx="16" cy="6" r="2.6" fill="currentColor" />
      <circle cx="6" cy="24" r="2.6" fill="currentColor" />
      <circle cx="26" cy="24" r="2.6" fill="currentColor" />
      <circle cx="16" cy="18" r="2" fill="currentColor" />
    </svg>
  );
}

// Mouse-driven depth offset for the hero canvas, small range, spring-smoothed
// so it trails the cursor instead of snapping. Disabled under prefers-reduced-motion.
function useParallax(range: number) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 60, damping: 20, mass: 0.4 });
  const springY = useSpring(y, { stiffness: 60, damping: 20, mass: 0.4 });
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (reduceMotion) return;
    function handleMouseMove(event: MouseEvent) {
      const nx = (event.clientX / window.innerWidth) * 2 - 1;
      const ny = (event.clientY / window.innerHeight) * 2 - 1;
      // Opposite direction of cursor movement, per the depth-effect brief.
      x.set(-nx * range);
      y.set(-ny * range);
    }
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [range, reduceMotion, x, y]);

  return { x: springX, y: springY };
}

// Sparse ambient particles drifting up through the dark space above the
// sphere. Randomized once per mount (not per render) so drift feels organic
// rather than looping visibly.
function Particles({ count = 18 }: { count?: number }) {
  const reduceMotion = useReducedMotion();
  const particles = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        top: 18 + Math.random() * 50,
        size: 1 + Math.random() * 2.5,
        duration: 9 + Math.random() * 9,
        delay: Math.random() * 8,
        drift: 36 + Math.random() * 56,
      })),
    [count],
  );

  if (reduceMotion) return null;

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-10 overflow-hidden">
      {particles.map((p) => (
        <motion.span
          key={p.id}
          className="absolute rounded-full bg-lime-300"
          style={{ left: `${p.left}%`, top: `${p.top}%`, width: p.size, height: p.size }}
          initial={{ opacity: 0, y: 0 }}
          animate={{ opacity: [0, 0.8, 0], y: -p.drift }}
          transition={{ duration: p.duration, delay: p.delay, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}

function ScrollIndicator() {
  return (
    <motion.div
      className="absolute inset-x-0 bottom-8 z-20 flex flex-col items-center gap-2 text-white/60"
      animate={{ opacity: [0.4, 1, 0.4] }}
      transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
    >
      <span className="text-xs font-medium uppercase tracking-[0.2em]">Scroll to explore</span>
      <ChevronDown className="h-4 w-4" strokeWidth={1.5} />
    </motion.div>
  );
}

// Shared vertical footprint for the sphere canvas and the particle overlay,
// so particles read as floating in the same space as the sphere rather
// than around a differently-sized box. Tuned so the visible arc reads as
// roughly half the viewport (2026-07-09 brief), up from the prior ~50-58vh.
const HERO_VISUAL_HEIGHT = "h-[58vh] sm:h-[62vh] lg:h-[66vh]";

function App() {
  const parallax = useParallax(12);
  const canvasContainerRef = useRef<HTMLDivElement>(null);
  const [screen, setScreen] = useState<"hero" | "map" | "corridors" | "corridor">("hero");
  const [selectedCityId, setSelectedCityId] = useState<string | null>(null);
  const [selectedCorridor, setSelectedCorridor] = useState<string | null>(null);
  const [hovered, setHovered] = useState(false);
  const [isExploring, setIsExploring] = useState(false);
  const [convergeSignal, setConvergeSignal] = useState(0);
  const [convergePoint, setConvergePoint] = useState<{ nx: number; ny: number } | null>(null);

  // Explicit focus management on screen change - found live, not assumed:
  // after an AnimatePresence swap removes whatever was focused (e.g. the
  // sphere's own accessible button) with nothing re-focused, Chromium's
  // Tab-from-nothing fallback lands on the new screen's first focusable
  // element directly (a map marker, a corridor card...), skipping the
  // fixed nav's logo/Log-in entirely on the very next forward Tab - reachable
  // only via two Shift+Tabs backward, confirmed reproducible via keyboard-
  // only AND mouse-driven transitions alike, so it's not about click
  // position. tabIndex={-1} here means focusable via this ref, not part of
  // the normal Tab sequence itself - this is a landmark to receive focus
  // on arrival (same pattern SPA route changes use to announce new content
  // to screen readers), not a new stop users tab into on their own.
  //
  // A callback ref, not useRef+useEffect keyed on `screen`: with
  // AnimatePresence mode="wait", the new screen's motion.div doesn't
  // actually mount until the OLD one's exit animation finishes, which
  // happens after the `screen` state update itself - an effect keyed on
  // `screen` fires too early and finds nothing to focus yet. A callback ref
  // fires exactly when React commits this specific DOM node, which is
  // already the right moment regardless of Framer Motion's own sequencing.
  //
  // Skipped on the very first mount on purpose: a genuinely fresh page
  // load already tabs correctly (logo -> Log in -> sphere, verified) since
  // nothing was ever focused-then-removed yet - forcing focus there too
  // would trade that correct behavior for the same "skips the nav" problem
  // this is fixing, just on first load instead of on navigation.
  const isFirstScreenMount = useRef(true);
  const focusNewScreen = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;
    if (isFirstScreenMount.current) {
      isFirstScreenMount.current = false;
      return;
    }
    node.focus();
  }, []);

  const handleExplore = useCallback(
    (clientX?: number, clientY?: number) => {
      if (isExploring) return;
      setIsExploring(true);

      const el = canvasContainerRef.current;
      if (el && clientX !== undefined && clientY !== undefined) {
        const rect = el.getBoundingClientRect();
        const nx = Math.max(-1, Math.min(1, ((clientX - rect.left) / rect.width) * 2 - 1));
        const ny = Math.max(-1, Math.min(1, -(((clientY - rect.top) / rect.height) * 2 - 1)));
        setConvergePoint({ nx, ny });
      }
      setConvergeSignal((s) => s + 1);

      // Matches the sphere's own GSAP exit duration (HeroSphere.tsx,
      // EXIT_DURATION=0.7s) so the map only appears once the sphere has
      // genuinely cleared the frame, not partway through its exit.
      window.setTimeout(() => {
        setScreen("map");
      }, 700);
    },
    [isExploring],
  );

  const handleSelectCity = useCallback((cityId: string) => {
    setSelectedCityId(cityId);
    setScreen("corridors");
  }, []);

  const handleSelectCorridor = useCallback((corridor: string) => {
    setSelectedCorridor(corridor);
    setScreen("corridor");
  }, []);

  const handleBackToMap = useCallback(() => {
    setScreen("map");
  }, []);

  const handleBackToCorridorList = useCallback(() => {
    setScreen("corridors");
  }, []);

  // Global "return to landing page" - resets every piece of in-progress
  // state lifted up to App (selectedCityId/Corridor, isExploring, hover,
  // converge), not just the screen itself, so a later visit to a city or
  // corridor starts fresh rather than resuming stale state. Local state
  // further down the tree (e.g. CorridorDetail's activeTab) doesn't need
  // resetting here - it already unmounts/remounts fresh via AnimatePresence
  // whenever screen changes away from and back to that component.
  const handleReturnHome = useCallback(() => {
    setIsExploring(false);
    setHovered(false);
    setConvergeSignal(0);
    setConvergePoint(null);
    setSelectedCityId(null);
    setSelectedCorridor(null);
    setScreen("hero");
  }, []);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLButtonElement>) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        const rect = event.currentTarget.getBoundingClientRect();
        handleExplore(rect.left + rect.width / 2, rect.top + rect.height / 2);
      }
    },
    [handleExplore],
  );

  return (
    <div className="relative h-screen w-full overflow-hidden bg-black font-sans text-white">
      <nav className="fixed inset-x-0 top-0 z-50 flex items-center justify-between px-6 py-5 sm:px-10">
        <button
          type="button"
          onClick={handleReturnHome}
          aria-label="Return to homepage"
          className="rounded-sm brightness-100 transition-[filter] duration-200 hover:brightness-125 hover:drop-shadow-[0_0_6px_rgba(124,255,59,0.65)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-lime-400"
        >
          <NetworkMark />
        </button>
        <button
          type="button"
          className="rounded-sm border border-white/30 px-4 py-1.5 text-sm text-white/90 transition-colors duration-200 hover:border-lime-400 hover:text-lime-400"
        >
          Log in
        </button>
      </nav>

      <AnimatePresence mode="wait">
        {screen === "hero" ? (
          <motion.div
            key="hero"
            ref={focusNewScreen}
            tabIndex={-1}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="absolute inset-0 outline-none"
          >
            <motion.div
              animate={isExploring ? { opacity: 0, y: -16 } : { opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="relative z-20 px-6 pt-20 sm:px-10 sm:pt-24 lg:pl-16 lg:pt-24"
            >
              <div className="max-w-3xl">
                <h1
                  className="font-bold leading-[1.08] tracking-tight"
                  style={{ fontSize: "clamp(2.25rem, 1.7rem + 3.4vw, 4.75rem)" }}
                >
                  Smarter Expansion. <span className="text-lime-400">Stronger</span> Decisions.
                </h1>
                <div className="mt-5 h-[3px] w-16 bg-lime-400" />
                <p className="mt-5 max-w-2xl text-base leading-relaxed text-white/60 sm:text-lg">
                  AI-powered intelligence to identify high-potential cities, best corridors, top
                  brokers and the right communities to expand with confidence.
                </p>
              </div>
            </motion.div>

            {/*
              Revolving 3D sphere - sphereGeometry textured with the hero
              photo, unlit (see HeroSphere.tsx), rotating continuously on Y.
              A THREE.Mesh isn't part of the accessibility tree, so mouse/
              touch interaction is wired directly on the mesh via
              onPointerOver/Out/Click (per the brief), while a separate
              invisible, pointer-events-none <button> of the same footprint
              right below preserves the keyboard path (Tab focus +
              Enter/Space).

              No WebGL postprocessing (Bloom/EffectComposer) here -
              measured, not assumed: with it, actual FPS in this environment
              (confirmed software-rendered WebGL via SwiftShader, no real
              GPU) collapsed to 3-15fps, even after cutting Bloom's own
              settings hard. The glow is a Fresnel rim-light shell mesh
              instead (see HeroSphere.tsx) - sharp, thin edge glow, one
              cheap extra draw call rather than a multi-pass pipeline.
            */}
            <motion.div
              ref={canvasContainerRef}
              style={{ x: parallax.x, y: parallax.y }}
              className={`absolute inset-x-0 bottom-0 z-[1] ${HERO_VISUAL_HEIGHT} ${hovered ? "cursor-pointer" : ""}`}
            >
              <Canvas camera={{ position: [0, 0, 4.9], fov: 48 }} gl={{ alpha: true, antialias: true }}>
                <Suspense fallback={null}>
                  <HeroSphere
                    hovered={hovered}
                    exploring={isExploring}
                    onPointerOver={() => setHovered(true)}
                    onPointerOut={() => setHovered(false)}
                    onClick={(e) => handleExplore(e.nativeEvent.clientX, e.nativeEvent.clientY)}
                  />
                </Suspense>
              </Canvas>
            </motion.div>

            <button
              type="button"
              aria-label="Explore the intelligence network"
              onKeyDown={handleKeyDown}
              className={`pointer-events-none absolute inset-x-0 bottom-0 z-[2] ${HERO_VISUAL_HEIGHT} appearance-none border-0 bg-transparent p-0 opacity-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-lime-400`}
            />

            {/*
              z-0, BELOW the sphere (z-1): R3F's <Canvas> forces pointer-
              events:auto on its own internal wrapper div via inline style,
              silently overriding a className="pointer-events-none" passed
              to it - so this layer could never truly be click-through if it
              sat above the sphere. Sitting below it instead sidesteps the
              problem entirely. See DECISIONS.md 2026-07-08.
            */}
            <div className={`pointer-events-none absolute inset-x-0 bottom-0 z-0 ${HERO_VISUAL_HEIGHT}`}>
              <ParticleOverlay hovered={hovered} convergeSignal={convergeSignal} convergePoint={convergePoint} />
            </div>

            <Particles />
            <ScrollIndicator />
          </motion.div>
        ) : screen === "map" ? (
          <motion.div
            key="map"
            ref={focusNewScreen}
            tabIndex={-1}
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="absolute inset-0 outline-none"
          >
            <IndiaMap onSelectCity={handleSelectCity} />
          </motion.div>
        ) : screen === "corridors" ? (
          selectedCityId && (
            <motion.div
              key="corridors"
              ref={focusNewScreen}
              tabIndex={-1}
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="absolute inset-0 outline-none"
            >
              <CorridorList cityId={selectedCityId} onSelectCorridor={handleSelectCorridor} onBack={handleBackToMap} />
            </motion.div>
          )
        ) : (
          selectedCityId &&
          selectedCorridor && (
            <motion.div
              key="corridor"
              ref={focusNewScreen}
              tabIndex={-1}
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="absolute inset-0 outline-none"
            >
              <CorridorDetail
                cityId={selectedCityId}
                corridor={selectedCorridor}
                onBack={handleBackToCorridorList}
              />
            </motion.div>
          )
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
