import { useEffect, useState } from "react";

// Fields read directly from brokers.json - confirmed live: contact_available
// is false for all 1571 rows (phone/company/contact_* all null, both by the
// site never exposing them and no GOOGLE_MAPS_API_KEY set upstream). Shown
// as one note, not five separate blank fields. sample_detail_url is only
// present for 35.5% of brokers (558/1571) - the exclusivity check it's
// computed with (a URL provably belongs to only this one poster city-wide)
// is intentionally strict, so most brokers genuinely have none; not typed
// as always-present, and only rendered as a link when it exists.
interface Broker {
  city_id: string;
  corridor: string;
  agent_display: string;
  listing_count: number;
  broker_activity_score: number;
  sample_detail_url: string | null;
  contact_available: boolean;
}

const PAGE_SIZE = 30;

export function BrokerTab({ cityId, corridor }: { cityId: string; corridor: string }) {
  const [brokers, setBrokers] = useState<Broker[] | null>(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
    fetch("/data/brokers.json")
      .then((res) => res.json())
      .then((data: Broker[]) =>
        setBrokers(data.filter((b) => b.city_id === cityId && b.corridor === corridor)),
      );
  }, [cityId, corridor]);

  if (brokers === null) {
    return <p className="text-sm text-white/50">Loading brokers...</p>;
  }

  if (brokers.length === 0) {
    return <p className="text-sm text-white/50">No brokers on record for this corridor yet.</p>;
  }

  const sorted = [...brokers].sort((a, b) => b.broker_activity_score - a.broker_activity_score);
  const visible = sorted.slice(0, visibleCount);

  return (
    <div>
      <p className="mb-3 text-xs text-white/40">
        {brokers.length} {brokers.length === 1 ? "broker" : "brokers"} active in this corridor
      </p>
      <div className="overflow-hidden rounded-sm border border-white/15">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-white/15 text-xs text-white/40">
              <th className="px-3 py-2 font-normal">Agent</th>
              <th className="px-3 py-2 font-normal">Listings</th>
              <th className="px-3 py-2 font-normal">Activity score</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((b, i) => (
              <tr key={`${b.agent_display}-${i}`} className="border-b border-white/5 text-white/80 last:border-0">
                <td className="px-3 py-2">
                  {b.sample_detail_url ? (
                    <a href={b.sample_detail_url} target="_blank" rel="noreferrer" className="hover:text-lime-400 hover:underline">
                      {b.agent_display}
                    </a>
                  ) : (
                    b.agent_display
                  )}
                </td>
                <td className="px-3 py-2">{b.listing_count}</td>
                <td className="px-3 py-2 text-lime-400">{b.broker_activity_score.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[11px] text-white/35">
        Verified phone/contact details unavailable for brokers in this data set - agent names link to a sample
        listing where one could be exclusively traced to them, plain text otherwise.
      </p>
      {visibleCount < sorted.length && (
        <button
          type="button"
          onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
          className="mt-4 rounded-sm border border-white/30 px-4 py-1.5 text-sm text-white/90 transition-colors duration-200 hover:border-lime-400 hover:text-lime-400"
        >
          Show more ({sorted.length - visibleCount} remaining)
        </button>
      )}
    </div>
  );
}
