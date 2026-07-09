import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

// Locally hosted, not hotlinked - dropped in directly by the user (2026-07-06,
// round 7 continued, Home page pass). Source/license text is intentionally
// NOT asserted here yet - unlike every other image in this app (see
// DECISIONS.md rounds 3-7), this one wasn't sourced or license-verified by
// this session, so claiming a license here would be a fabrication. Flagged
// as an open item until the real source/license/date is confirmed.
const HERO_IMAGE = "/assets/images/hero-global-network.jpg";

// Same "arrive, don't cut" timing IndiaNetworkMap already uses for its own
// click-to-navigate moment (550ms) - one shared duration convention for
// every "click something, watch it settle, then move on" interaction in
// this app, not a value invented fresh for this page.
const TRANSITION_SECONDS = 0.55;

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] as const } },
};

export function Home() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const [entering, setEntering] = useState(false);

  const enterExplorer = () => {
    if (entering) return; // ignore repeat activation (click then Enter, double-click) mid-transition
    if (reduceMotion) {
      navigate("/explore-map");
      return;
    }
    setEntering(true);
    setTimeout(() => navigate("/explore-map"), TRANSITION_SECONDS * 1000);
  };

  return (
    <button
      type="button"
      onClick={enterExplorer}
      aria-label="Enter City Explorer"
      className="group relative flex min-h-screen w-full cursor-pointer flex-col items-start justify-center overflow-hidden px-6 py-20 text-left sm:px-10 lg:px-14 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-6px] focus-visible:outline-accent-500"
    >
      <motion.div
        className="absolute inset-0"
        animate={
          entering
            ? { scale: 1.22, rotate: 7, filter: "blur(3px)" }
            : { scale: 1, rotate: 0, filter: "blur(0px)" }
        }
        transition={{ duration: reduceMotion ? 0 : TRANSITION_SECONDS, ease: [0.16, 1, 0.3, 1] }}
      >
        <img src={HERO_IMAGE} alt="" className="h-full w-full object-cover" />
        {/* Legibility scrim - the source image is a busy lit network map, this
            keeps the title/subtitle readable without relying on the raw
            image's own contrast, which varies a lot by continent/region. */}
        <div className="absolute inset-0 bg-void/55" />
        <div className="absolute inset-0 bg-gradient-to-t from-void via-void/45 to-void/15" />
        <div className="absolute inset-0 bg-gradient-to-r from-void/90 via-void/35 to-transparent" />
      </motion.div>

      <motion.div
        initial="hidden"
        animate={entering ? "hidden" : "show"}
        variants={{ show: { transition: { staggerChildren: 0.12 } } }}
        transition={{ duration: 0.25 }}
        className="relative z-10 max-w-2xl"
      >
        <motion.h1
          variants={fadeUp}
          className="font-display text-4xl font-semibold leading-[1.08] tracking-tight text-text-hi sm:text-6xl"
        >
          Smarter Expansion.
          <br />
          <span className="text-gradient-violet">Stronger Decisions.</span>
        </motion.h1>
        <motion.p variants={fadeUp} className="mt-5 max-w-xl text-base leading-relaxed text-text-lo sm:text-lg">
          Find the right cities, high-potential corridors, ideal societies, active brokers, and NRI
          outreach channels, all traced back to real, unfabricated data.
        </motion.p>

        {/* Hover/focus affordance - the globe itself is the control, this is
            the "so it's not a hidden click nobody finds" cue the brief asks
            for, not a second, separate button. A plain div, deliberately NOT
            a Framer Motion child of the staggered fadeUp group: Framer
            applies its animated opacity as an inline style, which beats the
            opacity-0 Tailwind class in specificity and would leave this
            permanently visible regardless of hover state - confirmed this
            the hard way (screenshotted with the mouse nowhere near the
            hero and the prompt was still showing) before switching it to a
            plain CSS-only hover/focus toggle. */}
        <div className="mt-8 flex items-center gap-2 text-sm font-medium text-accent-400 opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-focus-visible:opacity-100">
          Enter <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
        </div>
      </motion.div>
    </button>
  );
}
