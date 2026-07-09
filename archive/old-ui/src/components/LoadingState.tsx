import { motion } from "framer-motion";

/** Shared loading indicator - an actual animated visual (echoing the Signal
 * Ring motif), never bare "Loading..." text with nothing moving. */
export function LoadingState({ label = "Loading engine data" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24">
      <motion.svg width="40" height="40" viewBox="0 0 40 40" animate={{ rotate: 360 }} transition={{ duration: 1.1, repeat: Infinity, ease: "linear" }}>
        <circle cx="20" cy="20" r="16" stroke="var(--color-surface-hi)" strokeWidth="4" fill="none" />
        <circle
          cx="20" cy="20" r="16" stroke="var(--color-accent-500)" strokeWidth="4" fill="none"
          strokeLinecap="round" strokeDasharray="30 100"
        />
      </motion.svg>
      <span className="text-sm text-text-lo">{label}</span>
    </div>
  );
}
