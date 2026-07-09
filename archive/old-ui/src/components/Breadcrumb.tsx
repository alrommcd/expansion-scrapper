import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

interface Crumb {
  label: string;
  to?: string;
}

/**
 * Shared element across the whole flow, not reset per page (motion brief,
 * 2026-07-06): each crumb carries layoutId={`crumb-${label}`}, scoped by
 * the <LayoutGroup> in App.tsx. A crumb whose label already existed in the
 * PREVIOUS page's breadcrumb (e.g. "Pune" appearing in both CityView's and
 * SocietyFinder's trails) is the same layout element continuing, so Framer
 * Motion shifts it left smoothly instead of fading it out and back in.
 * A genuinely NEW segment (nothing shared it before) has no matching prior
 * layoutId, so it just fades and slides in on its own - exactly the
 * "existing segments shift, new segments append with a fade" behavior
 * asked for, with no manual bookkeeping about which labels are "new".
 */
export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav className="mb-6 flex flex-wrap items-center gap-1.5 text-sm">
      {items.map((item, i) => (
        <motion.span
          key={item.label}
          layoutId={`crumb-${item.label}`}
          layout
          className="flex items-center gap-1.5"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          {i > 0 && <ChevronRight size={14} className="text-text-faint" />}
          {item.to ? (
            <Link to={item.to} className="text-text-lo transition-colors hover:text-accent-400">
              {item.label}
            </Link>
          ) : (
            <span className="text-text-hi">{item.label}</span>
          )}
        </motion.span>
      ))}
    </nav>
  );
}
