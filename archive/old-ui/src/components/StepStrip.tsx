import { motion } from "framer-motion";

const STEPS = [
  { n: 1, title: "Select city", desc: "Choose a city to analyze" },
  { n: 2, title: "Top corridors", desc: "Ranked by fit_score, five locked gates" },
  { n: 3, title: "Choose focus", desc: "Society, broker, or NRI/absentee" },
  { n: 4, title: "Get insights", desc: "Traceable, never fabricated" },
];

export function StepStrip() {
  return (
    <div className="glass flex flex-col gap-6 rounded-2xl p-6 sm:flex-row sm:items-center sm:justify-between sm:gap-2">
      {STEPS.map((step, i) => (
        <div key={step.n} className="flex flex-1 items-center gap-4">
          <div className="flex items-center gap-4">
            <motion.div
              initial={{ scale: 0.6, opacity: 0 }}
              whileInView={{ scale: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, type: "spring", stiffness: 200, damping: 16 }}
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-mono text-sm font-semibold ${
                i === 0
                  ? "bg-accent-500 text-black"
                  : "bg-surface-hi text-text-lo"
              }`}
            >
              {step.n}
            </motion.div>
            <div>
              <div className="text-sm font-medium text-text-hi">{step.title}</div>
              <div className="text-xs text-text-lo">{step.desc}</div>
            </div>
          </div>
          {i < STEPS.length - 1 && (
            <div className="hidden h-px flex-1 bg-gradient-to-r from-line-hi to-transparent sm:block" />
          )}
        </div>
      ))}
    </div>
  );
}
