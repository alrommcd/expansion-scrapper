import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { AbsenteeCandidate, Broker, City, Corridor, NriDirectoryEntry, Society, Stats } from "../types";

export interface DataShape {
  cities: City[];
  corridors: Corridor[];
  societies: Society[];
  brokers: Broker[];
  candidates: AbsenteeCandidate[];
  directory: NriDirectoryEntry[];
  stats: Stats;
}

interface DataState {
  data: DataShape | null;
  loading: boolean;
  error: string | null;
}

const DataContext = createContext<DataState>({ data: null, loading: true, error: null });

async function loadJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`Failed to load ${path} (${res.status}). Run "python export_frontend_data.py" from the repo root.`);
  }
  return res.json() as Promise<T>;
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DataState>({ data: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [cities, corridors, societies, brokers, candidates, directory, stats] = await Promise.all([
          loadJson<City[]>("/data/cities.json"),
          loadJson<Corridor[]>("/data/corridors.json"),
          loadJson<Society[]>("/data/societies.json"),
          loadJson<Broker[]>("/data/brokers.json"),
          loadJson<AbsenteeCandidate[]>("/data/absentee_candidates.json"),
          loadJson<NriDirectoryEntry[]>("/data/nri_directory.json"),
          loadJson<Stats>("/data/stats.json"),
        ]);
        if (!cancelled) {
          setState({ data: { cities, corridors, societies, brokers, candidates, directory, stats }, loading: false, error: null });
        }
      } catch (e) {
        if (!cancelled) {
          setState({ data: null, loading: false, error: e instanceof Error ? e.message : String(e) });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return <DataContext.Provider value={state}>{children}</DataContext.Provider>;
}

export function useAppData() {
  return useContext(DataContext);
}
