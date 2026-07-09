export function plural(n: number, word: string, pluralWord?: string): string {
  return `${n} ${n === 1 ? word : pluralWord ?? `${word}s`}`;
}

export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

// Deterministic gradient per name, so the same corridor/society always gets
// the same placeholder tile color across the whole app (not random per render).
const GRADIENTS: [string, string][] = [
  ["#4C3A8F", "#8B5CF6"],
  ["#3730A3", "#6366F1"],
  ["#5B21B6", "#A855F7"],
  ["#1E1B4B", "#6D7BF7"],
  ["#7C2D12", "#F4A340"],
  ["#312E81", "#818CF8"],
];

export function gradientFor(seed: string): [string, string] {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return GRADIENTS[hash % GRADIENTS.length];
}

export function formatDays(days: number | null): string {
  if (days === null) return "unavailable";
  if (days === 0) return "today";
  if (days === 1) return "1 day";
  return `${days} days`;
}

export function formatCov(cov: number | null): string {
  if (cov === null) return "unavailable";
  return `${(cov * 100).toFixed(1)}% spread`;
}
