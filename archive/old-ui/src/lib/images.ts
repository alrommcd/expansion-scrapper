import { useEffect, useState } from "react";

export type ImageBucket = "cities" | "corridors" | "societies";

export interface ImageMeta {
  illustrative?: boolean;
}

export interface ImageManifest {
  cities: Record<string, string>;
  corridors: Record<string, string>;
  societies: Record<string, string>;
  meta: Record<ImageBucket, Record<string, ImageMeta>>;
}

const EMPTY_MANIFEST: ImageManifest = {
  cities: {},
  corridors: {},
  societies: {},
  meta: { cities: {}, corridors: {}, societies: {} },
};

function asStringRecord(value: unknown): Record<string, string> {
  if (typeof value !== "object" || value === null) return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (typeof v === "string") out[k] = v;
  }
  return out;
}

function asMetaRecord(value: unknown): Record<string, ImageMeta> {
  if (typeof value !== "object" || value === null) return {};
  const out: Record<string, ImageMeta> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (typeof v === "object" && v !== null) {
      const illustrative = (v as Record<string, unknown>).illustrative;
      out[k] = { illustrative: typeof illustrative === "boolean" ? illustrative : undefined };
    }
  }
  return out;
}

// Exported so the malformed-shape handling is directly unit-testable without
// a DOM/fetch: an unexpected shape (missing bucket, wrong type, stray keys)
// normalizes to an empty bucket for just that field, never throws, and never
// lets a bad manifest crash the whole lookup. `_meta` (illustrative-stock
// disclosure, e.g. "representative image" tags) is parsed the same
// defensive way - a missing/malformed _meta degrades to "no tag shown," not
// a crash, same philosophy as a missing image degrading to the placeholder.
export function parseManifest(raw: unknown): ImageManifest {
  if (typeof raw !== "object" || raw === null) return EMPTY_MANIFEST;
  const r = raw as Record<string, unknown>;
  const metaRaw = typeof r._meta === "object" && r._meta !== null ? (r._meta as Record<string, unknown>) : {};
  return {
    cities: asStringRecord(r.cities),
    corridors: asStringRecord(r.corridors),
    societies: asStringRecord(r.societies),
    meta: {
      cities: asMetaRecord(metaRaw.cities),
      corridors: asMetaRecord(metaRaw.corridors),
      societies: asMetaRecord(metaRaw.societies),
    },
  };
}

// Deliberately not wired through DataProvider: this is manually curated art
// direction (Mesa's own photos / licensed stock), not engine output, and
// export_frontend_data.py is documented as the ONLY Python-to-SPA bridge -
// mixing the two would blur that boundary. A missing, malformed, or oddly-
// shaped manifest all degrade to "every tile falls back to PlaceholderTile,"
// never a thrown error - see parseManifest for the shape-normalization half
// of that guarantee; the .catch below covers network failure and JSON parse
// failure (res.json() rejects on invalid JSON text, which skips straight to
// .catch, never reaching parseManifest with garbage).
let manifestPromise: Promise<ImageManifest> | null = null;

function loadManifest(): Promise<ImageManifest> {
  if (!manifestPromise) {
    manifestPromise = fetch("/assets/image-manifest.json")
      .then((res) => (res.ok ? res.json() : null))
      .then(parseManifest)
      .catch(() => EMPTY_MANIFEST);
  }
  return manifestPromise;
}

export function useImageManifest(): ImageManifest {
  const [manifest, setManifest] = useState<ImageManifest>(EMPTY_MANIFEST);

  useEffect(() => {
    let cancelled = false;
    loadManifest().then((m) => {
      if (!cancelled) setManifest(m);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return manifest;
}

// Namespacing keeps corridor/society names collision-free across cities
// (e.g. two cities could plausibly share a corridor name) without forcing
// whoever edits image-manifest.json to think about IDs instead of names.
export function corridorKey(cityName: string, corridor: string): string {
  return `${cityName}::${corridor}`;
}

export function societyKey(cityName: string, corridor: string, society: string): string {
  return `${cityName}::${corridor}::${society}`;
}
