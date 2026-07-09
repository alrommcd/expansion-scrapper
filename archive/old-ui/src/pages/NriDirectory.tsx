import { AlertTriangle, ExternalLink, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Breadcrumb } from "../components/Breadcrumb";
import { LoadingState } from "../components/LoadingState";
import { useAppData } from "../data/DataProvider";

export function NriDirectory() {
  const { data, loading } = useAppData();
  const [query, setQuery] = useState("");

  const entries = useMemo(() => {
    const rows = data?.directory ?? [];
    if (!query.trim()) return rows;
    const q = query.trim().toLowerCase();
    return rows.filter(
      (e) => e.group_name.toLowerCase().includes(q) || e.city_focus.toLowerCase().includes(q) || e.category.toLowerCase().includes(q)
    );
  }, [data, query]);

  if (loading) return <LoadingState />;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-10">
      <Breadcrumb items={[{ label: "Home", to: "/" }, { label: "NRI Community Directory" }]} />

      <h1 className="font-display text-2xl font-semibold text-text-hi">NRI Community Directory</h1>
      <p className="mt-1 text-sm text-text-lo">
        Public WhatsApp/Facebook group links, not tied to a specific city or corridor - a standalone
        outreach directory, separate from the scored engine layers above.
      </p>

      <div className="glass mt-5 flex items-start gap-3 rounded-xl border border-amber-500/20 p-4 text-sm">
        <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-400" />
        <span className="text-text-lo">
          This is a <strong className="text-text-hi">manual outreach directory</strong>, not a lead
          generator. It requires a human to open each link, judge relevance, and choose to engage. Group
          names are not always reliably tied to what a link leads to - vet before use.
        </span>
      </div>

      <div className="glass-hi mt-6 flex w-full items-center gap-2 rounded-xl px-3 py-2 sm:w-72">
        <Search size={16} className="text-text-faint" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by name, city, category..."
          className="w-full bg-transparent text-sm text-text-hi outline-none placeholder:text-text-faint"
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {entries.map((e, i) => (
          <a
            key={i}
            href={e.link}
            target="_blank"
            rel="noopener noreferrer"
            className="glass flex items-center justify-between gap-3 rounded-xl p-4 transition-colors hover:border-accent-500/40"
          >
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-text-hi">{e.group_name}</div>
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-text-lo">
                <span>{e.platform}</span>
                <span className="text-text-faint">&middot;</span>
                <span>{e.category}</span>
                {e.city_focus && (
                  <>
                    <span className="text-text-faint">&middot;</span>
                    <span>{e.city_focus}</span>
                  </>
                )}
              </div>
            </div>
            <ExternalLink size={15} className="shrink-0 text-text-faint" />
          </a>
        ))}
      </div>
      {entries.length === 0 && <div className="py-12 text-center text-sm text-text-lo">No entries match.</div>}
    </div>
  );
}
