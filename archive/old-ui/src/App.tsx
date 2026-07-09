import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { SourceInspectorProvider } from "./components/SourceInspector";
import { DataProvider } from "./data/DataProvider";
import { AbsenteeFinder } from "./pages/AbsenteeFinder";
import { BrokerFinder } from "./pages/BrokerFinder";
import { CityExplorer } from "./pages/CityExplorer";
import { CityView } from "./pages/CityView";
import { CorridorDetail } from "./pages/CorridorDetail";
import { Home } from "./pages/Home";
import { IndiaNetworkMap } from "./pages/IndiaNetworkMap";
import { NriDirectory } from "./pages/NriDirectory";
import { SocietyFinder } from "./pages/SocietyFinder";

function AnimatedRoutes() {
  const location = useLocation();
  const reduceMotion = useReducedMotion();

  // Reduced motion: a plain opacity fade, no slide/scale/blur/shared-element
  // morphing - the global CSS media query only forces CSS transition/
  // animation durations to ~0, it has no effect on Framer Motion's
  // JS-driven `animate` prop, so this has to be handled explicitly here.
  const variants = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : { initial: { opacity: 0, x: 12 }, animate: { opacity: 1, x: 0 }, exit: { opacity: 0, x: -12 } };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={variants.initial}
        animate={variants.animate}
        exit={variants.exit}
        transition={{ duration: reduceMotion ? 0.12 : 0.22, ease: [0.16, 1, 0.3, 1] }}
      >
        <Routes location={location}>
          <Route path="/" element={<Home />} />
          <Route path="/explore" element={<CityExplorer />} />
          <Route path="/explore-map" element={<IndiaNetworkMap />} />
          <Route path="/city/:cityId" element={<CityView />} />
          <Route path="/city/:cityId/corridor/:corridorName" element={<CorridorDetail />} />
          <Route path="/city/:cityId/corridor/:corridorName/society" element={<SocietyFinder />} />
          <Route path="/city/:cityId/corridor/:corridorName/broker" element={<BrokerFinder />} />
          <Route path="/city/:cityId/corridor/:corridorName/absentee" element={<AbsenteeFinder />} />
          <Route path="/directory" element={<NriDirectory />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

function App() {
  return (
    <BrowserRouter>
      <DataProvider>
        <SourceInspectorProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            {/* pt clears the mobile fixed topbar (Sidebar.tsx) - that topbar is
                position:fixed so it's not a flex sibling here, this padding is
                the only thing standing in for its height on narrow viewports. */}
            <main className="min-w-0 flex-1 pt-[62px] lg:pt-0">
              {/* LayoutGroup scopes layoutId matching (search bar, breadcrumb
                  segments, corridor-tile-to-header) across route changes -
                  without it, Framer Motion can't tell a layoutId on the
                  outgoing page's tree is "the same element" as one on the
                  incoming page's tree, since AnimatePresence unmounts/
                  remounts the whole subtree between routes. */}
              <LayoutGroup>
                <AnimatedRoutes />
              </LayoutGroup>
            </main>
          </div>
        </SourceInspectorProvider>
      </DataProvider>
    </BrowserRouter>
  );
}

export default App;
