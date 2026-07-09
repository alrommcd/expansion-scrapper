import { AnimatePresence, motion } from "framer-motion";
import { Building2, Home, Map, Menu, Users, X, ScanSearch } from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { CitySwitcher } from "./CitySwitcher";

// Corridor/Society/Broker/NRI finders are all reached via a chosen city's
// corridor drill-down (breadcrumb), not standalone top-level destinations
// with no city context - a nav item that opens to nothing real would be the
// exact kind of decorative structure the design brief warns against. Home
// and City Explorer are the two genuine entry points; the rest surface once
// a city/corridor is selected.
const REAL_NAV_ITEMS = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/explore", label: "City Explorer", icon: Map, end: false },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <div className="flex items-center gap-3 px-5 py-6">
        <svg width="30" height="30" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="12" fill="var(--color-surface-hi)" />
          <circle cx="24" cy="24" r="17" stroke="#2A2545" strokeWidth="3" />
          <circle
            cx="24" cy="24" r="17" stroke="var(--color-accent-500)" strokeWidth="3" strokeLinecap="round"
            strokeDasharray="80 200" transform="rotate(-90 24 24)"
          />
          <circle cx="24" cy="24" r="10" stroke="#2A2545" strokeWidth="3" />
          <circle
            cx="24" cy="24" r="10" stroke="var(--color-amber-400)" strokeWidth="3" strokeLinecap="round"
            strokeDasharray="38 63" transform="rotate(-90 24 24)"
          />
        </svg>
        <span className="font-display text-[15px] font-semibold tracking-tight text-text-hi">
          Expansion Intelligence
        </span>
      </div>

      <div className="mb-2">
        <CitySwitcher onNavigate={onNavigate} />
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {REAL_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.label}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                isActive
                  ? "bg-accent-600/20 text-text-hi border border-accent-500/30"
                  : "text-text-lo border border-transparent hover:bg-white/5 hover:text-text-hi"
              }`
            }
          >
            <item.icon size={18} strokeWidth={1.75} />
            {item.label}
          </NavLink>
        ))}

        <div className="mt-4 px-3 text-[11px] uppercase tracking-wider text-text-faint">Focus (via corridor)</div>
        {[
          { label: "Society Finder", icon: Building2 },
          { label: "Broker Finder", icon: Users },
          { label: "NRI / Absentee Finder", icon: ScanSearch },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-text-faint">
            <item.icon size={18} strokeWidth={1.75} />
            {item.label}
          </div>
        ))}
      </nav>

      <div className="px-5 py-5 text-[11px] leading-relaxed text-text-faint">
        Scores and figures are 100% machine-derived from the engine's exported data, never hand-entered. Tile
        imagery is a separate, manually curated layer, not analytical data, and falls back to a placeholder
        wherever none is supplied.
      </div>
    </>
  );
}

export function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile top bar - `fixed`, not `sticky`, so it's fully out of the parent
          flex row's layout flow. It previously used `sticky` inside a bare
          Fragment, which meant it and <aside> were BOTH direct flex-row
          children of App.tsx's `flex` container - as a flex item with no
          declared height, it stretched to the full row height (flex's
          default align-items: stretch) and squeezed <main> into a narrow
          leftover column. `fixed` removes it from flex sizing entirely. */}
      <div className="glass fixed inset-x-0 top-0 z-40 flex items-center justify-between px-4 py-3 lg:hidden">
        <span className="font-display text-sm font-semibold text-text-hi">Expansion Intelligence</span>
        <button
          onClick={() => setOpen(true)}
          className="rounded-lg p-2 text-text-lo hover:bg-white/5"
          aria-label="Open navigation"
        >
          <Menu size={20} />
        </button>
      </div>

      {/* Desktop fixed sidebar */}
      <aside className="glass sticky top-0 hidden h-screen w-64 flex-col lg:flex">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/60 lg:hidden"
              onClick={() => setOpen(false)}
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "tween", duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="glass-hi fixed inset-y-0 left-0 z-50 flex w-72 flex-col lg:hidden"
            >
              <button
                onClick={() => setOpen(false)}
                className="absolute right-3 top-4 rounded-lg p-2 text-text-lo hover:bg-white/5"
                aria-label="Close navigation"
              >
                <X size={18} />
              </button>
              <SidebarContent onNavigate={() => setOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
