import { useState, useEffect, useCallback } from "react";

/** This Week — the decisioning surface.
 *
 *  Ranked cards, each one decision: what we noticed, why it matters, and a
 *  button that actually does the thing (issue rewards, send CASL-gated texts).
 *  Every action is logged server-side and its outcome — redemptions, revenue
 *  back — attributes to the decision on every reload. Decide → act → measure.
 */

const apiBase = import.meta.env.VITE_API_BASE ?? "";

interface Person {
  user_id: string;
  name?: string;
  phone?: string;
  visits: number;
  total_spent_cents: number;
  avg_order_cents: number;
  last_order_at: string;
  days_since_last: number;
  cadence_days?: number | null;
  usual?: string | null;
}

interface ExpiringReward {
  reward_id: string;
  code: string;
  expires_at: string;
  days_left: number;
  user_id: string;
  name?: string;
  phone?: string;
  template_name: string;
}

interface WeekdayStat { weekday: string; avg_revenue_cents: number; active_dates: number; }

interface Card {
  key: string;
  priority: "act_now" | "worth_doing" | "watch" | "locked";
  headline: string;
  why: string;
  impact_cents?: number | null;
  impact_label?: string;
  evidence?: {
    people?: Person[];
    rewards?: ExpiringReward[];
    weekdays?: WeekdayStat[];
    median_avg_cents?: number;
    template?: { name: string; issued: number; redeemed: number; redemption_rate: number; revenue_cents: number };
    best?: { source_code: string; campaign_name?: string; scans: number; signups: number; rate: number };
    leak?: { source_code: string; campaign_name?: string; scans: number; signups: number; rate: number };
    total?: number;
  } | null;
  action?: { type: "send_offer" | "send_reminder" } | null;
}

interface Template { id: string; name: string; reward_type: string; reward_value: number; valid_days: number; }

interface PastAction {
  id: string;
  insight_key: string;
  action_type: string;
  template_name?: string | null;
  created_at: string;
  targeted_count: number;
  rewards_issued: number;
  already_had: number;
  sms_sent: number;
  sms_skipped: number;
  outcome: { redeemed: number; revenue_cents: number };
}

interface InsightsData {
  coverage: { orders: number; customers: number; first_order_at?: string | null; last_order_at?: string | null };
  cards: Card[];
  templates: Template[];
  default_template_id?: string | null;
  sms_configured: boolean;
  actions: PastAction[];
}

interface ActResult { targeted: number; rewards_issued: number; already_had: number; sms_sent: number; sms_skipped: number; already_reminded?: number; }

const PRIORITY: Record<Card["priority"], { label: string; chip: string; border: string }> = {
  act_now: { label: "Act now", chip: "bg-red-100 text-red-700", border: "border-l-red-500" },
  worth_doing: { label: "Worth doing", chip: "bg-amber-100 text-amber-700", border: "border-l-amber-400" },
  watch: { label: "Good to know", chip: "bg-gray-100 text-gray-600", border: "border-l-gray-300" },
  locked: { label: "Unlocks with data", chip: "bg-gray-100 text-gray-400", border: "border-l-gray-200" },
};

const INSIGHT_LABELS: Record<string, string> = {
  lapsed_regulars: "Win-back offer",
  one_and_done: "Second-visit offer",
  expiring_rewards: "Expiry reminder",
};

function money(cents: number, decimals = 0): string {
  return `$${(cents / 100).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

function rhythm(p: Person): string {
  const gone = Math.round(p.days_since_last);
  if (p.visits === 1) return `visited once · ${gone} days ago`;
  const cad = p.cadence_days != null ? `every ~${Math.round(p.cadence_days)} days` : "";
  return `came ${cad} · gone ${gone}`;
}

function daysAgo(iso: string): string {
  const d = Math.round((Date.now() - new Date(iso).getTime()) / 86400000);
  if (d <= 0) return "today";
  if (d === 1) return "yesterday";
  return `${d} days ago`;
}

interface Props { showToast: (message: string, type?: "success" | "error") => void; }

export default function DecisionsScreen({ showToast }: Props) {
  const [data, setData] = useState<InsightsData | null>(null);
  const [error, setError] = useState(false);
  // Per-card UI state, keyed by card.key.
  const [deselected, setDeselected] = useState<Record<string, Set<string>>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [chosenTemplate, setChosenTemplate] = useState<Record<string, string>>({});
  const [confirming, setConfirming] = useState<Record<string, boolean>>({});
  const [acting, setActing] = useState<Record<string, boolean>>({});
  const [receipts, setReceipts] = useState<Record<string, ActResult>>({});

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${apiBase}/api/admin/insights`, { credentials: "include" });
      if (!r.ok) throw new Error();
      const d = await r.json();
      setData(d.data);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function targetsFor(card: Card): string[] {
    const off = deselected[card.key] ?? new Set<string>();
    if (card.action?.type === "send_reminder") {
      return (card.evidence?.rewards ?? []).map(r => r.reward_id).filter(id => !off.has(id));
    }
    return (card.evidence?.people ?? []).map(p => p.user_id).filter(id => !off.has(id));
  }

  function toggleTarget(cardKey: string, id: string) {
    setDeselected(prev => {
      const next = new Set(prev[cardKey] ?? []);
      if (next.has(id)) next.delete(id); else next.add(id);
      return { ...prev, [cardKey]: next };
    });
  }

  function templateFor(card: Card): string {
    if (chosenTemplate[card.key]) return chosenTemplate[card.key];
    const ids = (data?.templates ?? []).map(t => t.id);
    if (data?.default_template_id && ids.includes(data.default_template_id)) return data.default_template_id;
    return ids[0] ?? "";
  }

  async function act(card: Card) {
    if (!card.action) return;
    const targets = targetsFor(card);
    setActing(prev => ({ ...prev, [card.key]: true }));
    try {
      const body =
        card.action.type === "send_offer"
          ? { insight_key: card.key, action_type: "send_offer", template_id: templateFor(card), user_ids: targets }
          : { insight_key: card.key, action_type: "send_reminder", reward_ids: targets };
      const r = await fetch(`${apiBase}/api/admin/insights/act`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || "Action failed");
      setReceipts(prev => ({ ...prev, [card.key]: d.data }));
      setConfirming(prev => ({ ...prev, [card.key]: false }));
      showToast("Done — outcome tracking started");
      load(); // refresh the past-actions ledger
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Action failed", "error");
    } finally {
      setActing(prev => ({ ...prev, [card.key]: false }));
    }
  }

  if (error) {
    return (
      <div>
        <h1 className="text-3xl font-bold mb-6">This week</h1>
        <div className="bg-white rounded-xl shadow-sm p-8 text-center text-gray-500">
          Couldn't load recommendations. <button onClick={load} className="text-red-600 underline">Try again</button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <h1 className="text-3xl font-bold mb-6">This week</h1>
        <p className="text-gray-400 py-12 text-center">Reading your history...</p>
      </div>
    );
  }

  const { coverage } = data;
  const activeCards = data.cards.filter(c => c.priority !== "locked");
  const lockedCards = data.cards.filter(c => c.priority === "locked");

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-1">This week</h1>
      <p className="text-sm text-gray-500 mb-6">
        Based on {coverage.orders} orders from {coverage.customers} customers
        {coverage.first_order_at && (
          <> · {new Date(coverage.first_order_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
            {" – "}{new Date(coverage.last_order_at!).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</>
        )}
      </p>

      {activeCards.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-10 text-center mb-6">
          <p className="text-lg font-medium mb-1">Nothing needs a decision right now.</p>
          <p className="text-sm text-gray-500">
            Cards appear here when regulars go quiet, rewards near expiry, or a pattern is worth acting on.
          </p>
        </div>
      )}

      <div className="space-y-4">
        {activeCards.map(card => (
          <DecisionCard
            key={card.key}
            card={card}
            templates={data.templates}
            smsConfigured={data.sms_configured}
            recentAction={data.actions.find(
              a => a.insight_key === card.key &&
                Date.now() - new Date(a.created_at).getTime() < 14 * 86400000
            )}
            targets={targetsFor(card)}
            deselected={deselected[card.key] ?? new Set()}
            onToggleTarget={id => toggleTarget(card.key, id)}
            expanded={!!expanded[card.key]}
            onToggleExpand={() => setExpanded(prev => ({ ...prev, [card.key]: !prev[card.key] }))}
            templateId={templateFor(card)}
            onTemplate={id => setChosenTemplate(prev => ({ ...prev, [card.key]: id }))}
            confirming={!!confirming[card.key]}
            onConfirm={v => setConfirming(prev => ({ ...prev, [card.key]: v }))}
            acting={!!acting[card.key]}
            receipt={receipts[card.key]}
            onAct={() => act(card)}
          />
        ))}
      </div>

      {lockedCards.map(card => (
        <div key={card.key} className="mt-4 bg-white/60 rounded-xl border border-dashed border-gray-300 p-5">
          <p className="text-sm font-medium text-gray-500">🔒 {card.headline}</p>
          <p className="text-sm text-gray-400 mt-1">{card.why}</p>
        </div>
      ))}

      {data.actions.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-bold mb-1">What you've acted on</h2>
          <p className="text-sm text-gray-500 mb-3">Results update live — every redemption traces back to the decision that caused it.</p>
          <div className="bg-white rounded-xl shadow-sm divide-y">
            {data.actions.map(a => <ActionRow key={a.id} action={a} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function ActionRow({ action: a }: { action: PastAction }) {
  const label = INSIGHT_LABELS[a.insight_key] ?? a.insight_key;
  const isOffer = a.action_type === "send_offer";
  const fresh = Date.now() - new Date(a.created_at).getTime() < 7 * 86400000;
  return (
    <div className="p-4 flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium">
          {label}
          {a.template_name && <span className="text-gray-500"> — {a.template_name}</span>}
          <span className="text-gray-400"> · {daysAgo(a.created_at)}</span>
        </p>
        <p className="text-xs text-gray-500 mt-0.5">
          {isOffer
            ? `${a.rewards_issued} issued${a.already_had ? ` · ${a.already_had} already had one` : ""} · ${a.sms_sent} texted${a.sms_skipped ? ` · ${a.sms_skipped} not texted` : ""}`
            : `${a.targeted_count} reminded · ${a.sms_sent} texted${a.sms_skipped ? ` · ${a.sms_skipped} not texted` : ""}`}
        </p>
      </div>
      <div className="text-right shrink-0">
        {a.outcome.redeemed > 0 ? (
          <>
            <p className="text-sm font-semibold text-green-700">{money(a.outcome.revenue_cents, 2)} back</p>
            <p className="text-xs text-gray-500">{a.outcome.redeemed} used</p>
          </>
        ) : (
          <p className="text-xs text-gray-400">{fresh ? "early days" : "no returns yet"}</p>
        )}
      </div>
    </div>
  );
}

interface CardProps {
  card: Card;
  templates: Template[];
  smsConfigured: boolean;
  recentAction?: PastAction;
  targets: string[];
  deselected: Set<string>;
  onToggleTarget: (id: string) => void;
  expanded: boolean;
  onToggleExpand: () => void;
  templateId: string;
  onTemplate: (id: string) => void;
  confirming: boolean;
  onConfirm: (v: boolean) => void;
  acting: boolean;
  receipt?: ActResult;
  onAct: () => void;
}

const PREVIEW_ROWS = 5;

function DecisionCard(props: CardProps) {
  const { card, templates, smsConfigured, recentAction, targets, deselected,
    onToggleTarget, expanded, onToggleExpand, templateId, onTemplate,
    confirming, onConfirm, acting, receipt, onAct } = props;
  const p = PRIORITY[card.priority];
  const template = templates.find(t => t.id === templateId);
  const isOffer = card.action?.type === "send_offer";

  return (
    <div className={`bg-white rounded-xl shadow-sm border-l-4 ${p.border} p-6`}>
      <div className="flex items-center gap-3 mb-2">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${p.chip}`}>{p.label}</span>
        {card.impact_cents != null && card.impact_cents > 0 && (
          <span className="text-xs text-green-700 font-medium">≈ {money(card.impact_cents)} {card.impact_label ?? ""}</span>
        )}
      </div>
      <h3 className="text-xl font-semibold mb-1.5">{card.headline}</h3>
      <p className="text-sm text-gray-600 leading-relaxed mb-4">{card.why}</p>

      {recentAction && !receipt && (
        <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2 mb-3">
          You acted on this {daysAgo(recentAction.created_at)} — {recentAction.rewards_issued || recentAction.targeted_count} people,{" "}
          {recentAction.outcome.redeemed} came back so far. Sending again is safe: nobody gets a second copy of the same reward.
        </p>
      )}

      {card.evidence?.people && (
        <PeopleTable
          people={card.evidence.people}
          total={card.evidence.total ?? card.evidence.people.length}
          selectable={!!card.action && !receipt}
          deselected={deselected}
          onToggle={onToggleTarget}
          expanded={expanded}
          onToggleExpand={onToggleExpand}
          idOf={person => person.user_id}
        />
      )}

      {card.evidence?.rewards && (
        <div className="mb-4 divide-y border rounded-lg">
          {(expanded ? card.evidence.rewards : card.evidence.rewards.slice(0, PREVIEW_ROWS)).map(r => (
            <label key={r.reward_id} className="flex items-center gap-3 px-3 py-2 text-sm cursor-pointer hover:bg-gray-50">
              {!receipt && (
                <input type="checkbox" checked={!deselected.has(r.reward_id)}
                  onChange={() => onToggleTarget(r.reward_id)} className="accent-red-600" />
              )}
              <span className="font-medium w-36 truncate">{r.name || r.phone || "Customer"}</span>
              <span className="font-mono text-xs text-gray-500">{r.code}</span>
              <span className="text-gray-500">{r.template_name}</span>
              <span className={`ml-auto text-xs font-semibold ${r.days_left <= 2 ? "text-red-600" : "text-amber-600"}`}>
                {Math.ceil(r.days_left)}d left
              </span>
            </label>
          ))}
          {card.evidence.rewards.length > PREVIEW_ROWS && (
            <button onClick={onToggleExpand} className="w-full py-2 text-xs text-red-600 hover:bg-gray-50">
              {expanded ? "Show fewer" : `Show all ${card.evidence.rewards.length}`}
            </button>
          )}
        </div>
      )}

      {card.evidence?.weekdays && (
        <div className="mb-2 space-y-1.5">
          {card.evidence.weekdays.map(w => {
            const max = Math.max(...card.evidence!.weekdays!.map(x => x.avg_revenue_cents), 1);
            return (
              <div key={w.weekday} className="flex items-center gap-2 text-xs">
                <span className="w-20 text-gray-500">{w.weekday}</span>
                <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                  <div className="h-full bg-red-400 rounded" style={{ width: `${(w.avg_revenue_cents / max) * 100}%` }} />
                </div>
                <span className="w-16 text-right text-gray-600">{money(w.avg_revenue_cents)}</span>
              </div>
            );
          })}
        </div>
      )}

      {card.evidence?.template && (
        <div className="flex gap-6 text-sm text-gray-600 mb-2">
          <span><b>{card.evidence.template.issued}</b> issued</span>
          <span><b>{card.evidence.template.redeemed}</b> used</span>
          <span><b>{Math.round(card.evidence.template.redemption_rate * 100)}%</b> redemption</span>
          <span><b>{money(card.evidence.template.revenue_cents)}</b> through the door</span>
        </div>
      )}

      {card.evidence?.best && card.evidence?.leak && (
        <div className="grid grid-cols-2 gap-3 mb-2 text-sm">
          {[card.evidence.best, card.evidence.leak].map((s, i) => (
            <div key={s.source_code} className={`rounded-lg border p-3 ${i === 0 ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
              <p className="font-medium">{s.campaign_name || s.source_code}</p>
              <p className="text-xs text-gray-600">{s.scans} scans → {s.signups} signups ({Math.round(s.rate * 100)}%)</p>
            </div>
          ))}
        </div>
      )}

      {/* Action area */}
      {receipt ? (
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-800">
          ✓ Done — {isOffer
            ? `${receipt.rewards_issued} reward${receipt.rewards_issued !== 1 ? "s" : ""} issued · ${receipt.sms_sent} texted` +
              (receipt.already_had ? ` · ${receipt.already_had} already had one` : "") +
              (receipt.sms_skipped ? ` · ${receipt.sms_skipped} not texted ${smsConfigured ? "(no consent)" : "(texting off)"}` : "")
            : `${receipt.sms_sent} texted` +
              (receipt.sms_skipped ? ` · ${receipt.sms_skipped} skipped ${smsConfigured ? "(no consent)" : "(texting off)"}` : "") +
              (receipt.already_reminded ? ` · ${receipt.already_reminded} reminded recently, left alone` : "")}
          <span className="block text-xs text-green-700 mt-1">Watch "What you've acted on" below — returns attribute back here automatically.</span>
        </div>
      ) : card.action && (
        confirming ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
            <p className="text-sm text-amber-900 mb-3">
              {isOffer ? (
                <>Issues <b>{template?.name ?? "a reward"}</b> to <b>{targets.length}</b> {targets.length === 1 ? "person" : "people"} (valid {template?.valid_days} days).
                  {" "}Texts go only to those who opted in{smsConfigured ? "" : " — texting is currently off (no mailing address on file)"};
                  everyone else still sees it on their next visit and at the Front Desk.</>
              ) : (
                <>Texts up to <b>{targets.length}</b> reward holder{targets.length === 1 ? "" : "s"} whose reward is about to expire.
                  Only people who opted in are texted{smsConfigured ? "" : " — and texting is currently off (no mailing address on file), so this may reach nobody"}.</>
              )}
            </p>
            <div className="flex gap-2">
              <button onClick={onAct} disabled={acting}
                className="px-4 py-1.5 bg-red-600 text-white text-sm font-semibold rounded-lg disabled:opacity-50">
                {acting ? "Sending..." : "Send it"}
              </button>
              <button onClick={() => onConfirm(false)} disabled={acting}
                className="px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            {isOffer && (
              <select value={templateId} onChange={e => onTemplate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-red-500">
                {templates.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.name} · {t.reward_type === "fixed" ? money(t.reward_value) : `${t.reward_value}%`} · {t.valid_days}d
                  </option>
                ))}
              </select>
            )}
            <button onClick={() => onConfirm(true)} disabled={targets.length === 0 || (isOffer && !templateId)}
              className="px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-lg disabled:opacity-40">
              {isOffer
                ? `Send offer to ${targets.length} ${targets.length === 1 ? "person" : "people"}`
                : `Text ${targets.length} reward holder${targets.length === 1 ? "" : "s"}`}
            </button>
          </div>
        )
      )}
    </div>
  );
}

interface PeopleTableProps {
  people: Person[];
  total: number;
  selectable: boolean;
  deselected: Set<string>;
  onToggle: (id: string) => void;
  expanded: boolean;
  onToggleExpand: () => void;
  idOf: (p: Person) => string;
}

function PeopleTable({ people, total, selectable, deselected, onToggle, expanded, onToggleExpand, idOf }: PeopleTableProps) {
  const rows = expanded ? people : people.slice(0, PREVIEW_ROWS);
  return (
    <div className="mb-4 border rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 border-b bg-gray-50">
            {selectable && <th className="pl-3 py-2 w-8"></th>}
            <th className="py-2 px-2">Who</th>
            <th className="py-2 px-2">Their rhythm</th>
            <th className="py-2 px-2 text-right">Visits</th>
            <th className="py-2 px-2 text-right">Avg ticket</th>
            <th className="py-2 px-2">Usually</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(person => {
            const id = idOf(person);
            return (
              <tr key={id} className={`border-b last:border-0 ${deselected.has(id) ? "opacity-40" : ""}`}>
                {selectable && (
                  <td className="pl-3">
                    <input type="checkbox" checked={!deselected.has(id)} onChange={() => onToggle(id)} className="accent-red-600" />
                  </td>
                )}
                <td className="py-2 px-2">
                  <span className="font-medium">{person.name || "No name"}</span>
                  <span className="block text-xs text-gray-400 font-mono">{person.phone}</span>
                </td>
                <td className="py-2 px-2 text-gray-600">{rhythm(person)}</td>
                <td className="py-2 px-2 text-right">{person.visits}</td>
                <td className="py-2 px-2 text-right">{money(person.avg_order_cents)}</td>
                <td className="py-2 px-2 text-gray-600 truncate max-w-[10rem]">{person.usual || "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {(people.length > PREVIEW_ROWS || total > people.length) && (
        <button onClick={onToggleExpand} className="w-full py-2 text-xs text-red-600 hover:bg-gray-50 border-t">
          {expanded
            ? "Show fewer"
            : `Show all ${people.length}${total > people.length ? ` (of ${total} total)` : ""}`}
        </button>
      )}
    </div>
  );
}
