interface SourceData {
  source_code: string;
  campaign_name: string | null;
  scans: number;
  signups: number;
  rewards_issued: number;
  redirects: number;
  orders: number;
  revenue_cents: number;
  // Conversion rates (%); null when the upstream count is 0.
  scan_to_signup_rate: number | null;
  signup_to_order_rate: number | null;
}

interface ActivityItem {
  type: string;
  source_code: string | null;
  created_at: string;
  detail: string | null;
}

export interface AnalyticsData {
  summary: {
    today: { scans: number; signups: number; rewards_issued: number; rewards_redeemed: number; redirects: number; orders: number; revenue_cents: number };
    period: { scans: number; signups: number; rewards_issued: number; rewards_redeemed: number; redirects: number; orders: number; revenue_cents: number };
  };
  funnel: { qr_scans: number; signups: number; rewards_issued: number; redirects: number; orders: number; scan_to_signup_rate: number | null; signup_to_order_rate: number | null };
  sources: SourceData[];
  sms_opt_in_rate: number;
  daily_volume: { day: string; orders: number; revenue_cents: number }[];
  top_dishes: { name: string; total_quantity: number; order_count: number }[];
  status_breakdown: Record<string, number>;
  recent_activity: ActivityItem[];
  days: number;
}

const ACTIVITY_LABELS: Record<string, { label: string; color: string }> = {
  scan: { label: "QR Scan", color: "bg-blue-500" },
  signup: { label: "Signup", color: "bg-green-500" },
  reward_issued: { label: "Reward Issued", color: "bg-amber-500" },
  reward_redeemed: { label: "Reward Redeemed", color: "bg-purple-500" },
  redirect: { label: "Order Redirect", color: "bg-indigo-500" },
  order: { label: "Order Placed", color: "bg-red-500" },
};

function formatTime(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return d.toLocaleDateString();
}

export function AnalyticsPanel({ data }: { data: AnalyticsData }) {
  // SCRUM-238: this panel's own "today" tile row was deleted — it duplicated
  // the dashboard's hero cards in a second visual style (SMS Opt-in rendered
  // three times on one page). The heroes in App.tsx are the single source;
  // this panel now renders only the ranged Trends content (funnel, series).
  const { funnel, sources } = data;
  const maxFunnel = Math.max(funnel.qr_scans, funnel.signups, funnel.rewards_issued, funnel.redirects, funnel.orders, 1);
  const maxOrders = Math.max(...data.daily_volume.map((d) => d.orders), 1);
  const maxQty = Math.max(...data.top_dishes.map((d) => d.total_quantity), 1);

  const topSources = sources.slice(0, 5);

  return (
    <div className="mt-4 space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold mb-4">Acquisition Funnel</h3>
          <div className="space-y-3">
            {[
              { label: "QR Scans", value: funnel.qr_scans },
              { label: "Signups", value: funnel.signups },
              { label: "Rewards Issued", value: funnel.rewards_issued },
              { label: "Order Redirects", value: funnel.redirects },
              { label: "Orders Placed", value: funnel.orders },
            ].map((stage, i) => {
              const pct = maxFunnel > 0 ? (stage.value / maxFunnel) * 100 : 0;
              return (
                <div key={stage.label}>
                  {i > 0 && (
                    <div className="flex items-center gap-2 mb-1 ml-2">
                      <div className="w-px h-4 border-l-2 border-dashed border-gray-300" />
                      <span className="text-xs text-gray-400">
                        {(() => {
                          const prev = [funnel.qr_scans, funnel.signups, funnel.rewards_issued, funnel.redirects, funnel.orders][i - 1];
                          const conv = prev > 0 ? ((stage.value / prev) * 100).toFixed(0) : "0";
                          const dropOff = prev - stage.value;
                          return `${conv}% conversion${dropOff > 0 ? ` (${dropOff} dropped)` : ""}`;
                        })()}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-600 w-32 flex-shrink-0">{stage.label}</span>
                    <div className="flex-1 h-7 bg-gray-100 rounded-md overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-red-500 to-red-400 rounded-md transition-all flex items-center px-2 min-w-[2rem]"
                        style={{ width: `${pct}%` }}
                      >
                        <span className="text-xs text-white font-medium">{stage.value.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold mb-4">Top Sources</h3>
          {topSources.length > 0 ? (
            <div className="space-y-4">
              {topSources.map((src) => (
                <div key={src.source_code}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-gray-700 truncate">
                      {src.campaign_name || src.source_code}
                    </span>
                    <span className="text-xs text-gray-400">
                      {src.orders} orders · ${(src.revenue_cents / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    {src.scans > 0 && (
                      <div
                        className="h-2 bg-blue-400 rounded-full"
                        style={{ flex: src.scans }}
                        title={`${src.scans} scans`}
                      />
                    )}
                    {src.signups > 0 && (
                      <div
                        className="h-2 bg-green-400 rounded-full"
                        style={{ flex: src.signups }}
                        title={`${src.signups} signups`}
                      />
                    )}
                    {src.rewards_issued > 0 && (
                      <div
                        className="h-2 bg-amber-400 rounded-full"
                        style={{ flex: src.rewards_issued }}
                        title={`${src.rewards_issued} rewards`}
                      />
                    )}
                    {src.redirects > 0 && (
                      <div
                        className="h-2 bg-indigo-400 rounded-full"
                        style={{ flex: src.redirects }}
                        title={`${src.redirects} redirects`}
                      />
                    )}
                  </div>
                  <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-xs text-gray-400">
                    <span>{src.scans} scans</span>
                    {src.signups > 0 && <span>{src.signups} signups</span>}
                    {src.rewards_issued > 0 && <span>{src.rewards_issued} rewards</span>}
                    {src.redirects > 0 && <span>{src.redirects} redirects</span>}
                    {src.scan_to_signup_rate != null && (
                      <span className="text-gray-500">{src.scan_to_signup_rate}% scan→signup</span>
                    )}
                    {src.signup_to_order_rate != null && (
                      <span className="text-gray-500">{src.signup_to_order_rate}% signup→order</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No source data yet</p>
          )}
          <div className="mt-4 flex gap-3 text-xs">
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-400 rounded-sm inline-block" /> Scans</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-400 rounded-sm inline-block" /> Signups</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-400 rounded-sm inline-block" /> Rewards</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-indigo-400 rounded-sm inline-block" /> Redirects</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold mb-4">Order Volume</h3>
          <div className="space-y-2">
            {data.daily_volume?.length > 0 ? (
              data.daily_volume.map((d) => (
                <div key={d.day} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-20 text-right">{d.day.slice(5)}</span>
                  <div className="flex-1 h-6 bg-gray-100 rounded-md overflow-hidden">
                    <div
                      className="h-full bg-red-500 rounded-md transition-all flex items-center px-2"
                      style={{ width: `${(d.orders / maxOrders) * 100}%` }}
                    >
                      <span className="text-xs text-white font-medium">{d.orders} orders</span>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500 w-16">${(d.revenue_cents / 100).toFixed(0)}</span>
                </div>
              ))
            ) : (
              <p className="text-gray-400 text-sm">No orders in this period</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold mb-4">Top 10 Dishes</h3>
          {data.top_dishes?.length > 0 ? (
            <div className="space-y-2">
              {data.top_dishes.map((d, i) => (
                <div key={d.name} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-5 text-right font-bold">{i + 1}</span>
                  <div className="flex-1">
                    <div className="flex justify-between text-sm mb-0.5">
                      <span className="font-medium text-gray-700 truncate">{d.name}</span>
                      <span className="text-gray-500 ml-2">x{d.total_quantity}</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-red-500 rounded-full transition-all"
                        style={{ width: `${(d.total_quantity / maxQty) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No dish data yet</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold mb-4">Status Breakdown</h3>
          {Object.keys(data.status_breakdown).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(data.status_breakdown).map(([s, c]) => (
                <div key={s} className="flex justify-between text-sm">
                  <span className="text-gray-600 capitalize">{s.replace("_", " ")}</span>
                  <span className="font-medium">{c}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No orders yet</p>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold mb-4">Recent Activity</h3>
          {data.recent_activity?.length > 0 ? (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {data.recent_activity.map((item, i) => {
                const meta = ACTIVITY_LABELS[item.type] || { label: item.type, color: "bg-gray-400" };
                return (
                  <div key={i} className="flex items-start gap-3">
                    <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${meta.color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-gray-700">{meta.label}</span>
                        {item.source_code && (
                          <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{item.source_code}</span>
                        )}
                      </div>
                      {item.detail && <p className="text-xs text-gray-500 mt-0.5 truncate">{item.detail}</p>}
                    </div>
                    <span className="text-xs text-gray-400 flex-shrink-0">{formatTime(item.created_at)}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No activity yet</p>
          )}
        </div>
      </div>
    </div>
  );
}


