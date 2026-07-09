import { motion } from "framer-motion";
import { ExternalLink, type LucideIcon } from "lucide-react";
import { FileSearch, ScanLine, MapPinCheck, Gauge } from "lucide-react";
import type { AbsenteeCandidate } from "../types";

const SIGNAL_LABEL: Record<string, string> = {
  multi_property_owner: "Multi-property owner",
  never_occupied: "Never occupied",
};

interface Node {
  icon: LucideIcon;
  label: string;
  value: string;
  muted?: boolean;
  title?: string;
}

/**
 * The product's credibility spine, made literal: every flagged candidate is
 * one raw listing carried through 4 real, inspectable stages. Every value
 * here is a real field off this exact AbsenteeCandidate row - nothing
 * aggregated, nothing invented. A stage with no recovered value says so
 * plainly (muted, "not captured") rather than being skipped, so the chain
 * never silently implies more confirmation than exists.
 */
export function PipelineLineage({ candidate: c }: { candidate: AbsenteeCandidate }) {
  const recoveredValue = c.address_recovered || c.owner_note || null;

  const nodes: Node[] = [
    {
      icon: FileSearch,
      label: "Raw listing",
      value: `#${c.listing_id} - ${c.society ?? "society unavailable"}, ${c.corridor}`,
    },
    {
      icon: ScanLine,
      label: SIGNAL_LABEL[c.signal_matched] ?? c.signal_matched,
      value: c.evidence || "signal matched, detail not retained",
      muted: !c.evidence,
      title: c.evidence || undefined,
    },
    {
      icon: MapPinCheck,
      label: c.address_recovered ? "Address recovered" : c.owner_note ? "Owner note" : "Recovered",
      value: recoveredValue ?? "not captured at detail-page recovery",
      muted: !recoveredValue,
    },
    {
      icon: Gauge,
      label: "Score",
      value: `${c.score} - posted ${c.days_since_posted ?? "?"}d ago`,
    },
  ];

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch sm:gap-0">
      {nodes.map((n, i) => (
        <div key={n.label} className="flex flex-1 items-center gap-3 sm:flex-col sm:items-stretch sm:gap-0">
          <div className="flex items-center gap-3 sm:flex-col sm:items-center sm:gap-2 sm:text-center">
            <motion.div
              initial={{ scale: 0.7, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.06, type: "spring", stiffness: 220, damping: 18 }}
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                n.muted ? "bg-surface-hi text-text-faint" : "bg-accent-500/15 text-accent-300"
              }`}
            >
              <n.icon size={15} strokeWidth={1.75} />
            </motion.div>
            <div className="min-w-0 sm:mt-1">
              <div className="text-[11px] uppercase tracking-wide text-text-faint">{n.label}</div>
              <div
                title={n.title}
                className={`truncate text-xs sm:max-w-[13rem] ${n.muted ? "italic text-text-faint" : "text-text-hi"}`}
              >
                {n.value}
              </div>
            </div>
          </div>
          {i < nodes.length - 1 && (
            <div className="ml-4 h-6 w-px bg-line-hi sm:ml-0 sm:mt-4 sm:h-px sm:w-full sm:flex-1" />
          )}
        </div>
      ))}
      {c.detail_url && (
        <a
          href={c.detail_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 flex shrink-0 items-center justify-center gap-1.5 rounded-lg bg-accent-500/15 px-3 py-2 text-xs font-medium text-accent-300 hover:bg-accent-500/25 sm:mt-0 sm:ml-3"
        >
          Source <ExternalLink size={12} />
        </a>
      )}
    </div>
  );
}
