import type { LucideIcon } from "lucide-react";

interface NotScoredStateProps {
  icon: LucideIcon;
  title: string;
  reason: string;
}

/**
 * The explicit "this city has no society layer yet" state (and similar gaps).
 * Never an empty table, never a spinner that never resolves - a clear,
 * specific reason, same honesty standard the engine itself holds to.
 */
export function NotScoredState({ icon: Icon, title, reason }: NotScoredStateProps) {
  return (
    <div className="glass flex flex-col items-center gap-4 rounded-2xl px-8 py-16 text-center">
      <div className="rounded-2xl bg-surface-hi p-4">
        <Icon size={28} strokeWidth={1.5} className="text-text-faint" />
      </div>
      <div className="space-y-1.5">
        <p className="font-display text-lg font-medium text-text-hi">{title}</p>
        <p className="max-w-md text-sm leading-relaxed text-text-lo">{reason}</p>
      </div>
    </div>
  );
}
