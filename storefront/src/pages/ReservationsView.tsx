import { useState } from "react";
import { api } from "../lib/api";
import { STATUS_COLORS, STATUS_LABEL, formatReservationForCopy } from "../lib/types";

interface Props {
  reservations: any[];
  onUpdate: () => void;
}

export function ReservationsView({ reservations, onUpdate }: Props) {
  const activeCount = reservations.filter(r => r.status !== "cancelled" && r.status !== "no_show").length;

  return (
    <main className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">Today's Reservations</h2>
        <span className="text-sm font-medium text-gray-500 bg-white rounded-full px-3 py-1 border">
          {activeCount} active
        </span>
      </div>

      {reservations.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-5xl mb-3" aria-hidden="true">📅</p>
          <p className="text-xl font-bold text-gray-500" role="status">No reservations today</p>
          <p className="text-base mt-1 text-gray-400">Reservations for today will appear here</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reservations.map((r: any) => (
            <ReservationCard key={r.id} reservation={r} onUpdate={onUpdate} />
          ))}
        </div>
      )}
    </main>
  );
}

function ReservationCard({ reservation, onUpdate }: { reservation: any; onUpdate: () => void }) {
  const [status, setStatus] = useState(reservation.status);
  const [copied, setCopied] = useState(false);

  async function updateStatus(newStatus: string) {
    try {
      const res = await fetch(api(`/api/storefront/reservations/${reservation.id}/status`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) { setStatus(newStatus); onUpdate(); }
    } catch {}
  }

  function handleCopy() {
    navigator.clipboard.writeText(formatReservationForCopy({ ...reservation, status })).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-lg font-bold text-gray-800">{reservation.guest_name}</p>
          <p className="text-base text-gray-600 mt-0.5">{reservation.guest_phone} &middot; {reservation.party_size} {reservation.party_size === 1 ? "guest" : "guests"}</p>
          {reservation.notes && <p className="text-sm text-gray-400 mt-1 italic">"{reservation.notes}"</p>}
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-gray-800">{reservation.start_time?.slice(0, 5)}</p>
          <span className={`inline-block mt-1 text-sm font-bold px-3 py-1 rounded-xl border min-w-[44px] text-center ${STATUS_COLORS[status] || "bg-gray-100"}`}>
            {STATUS_LABEL[status] || status}
          </span>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap pt-2 border-t border-gray-100">
        {status === "confirmed" && (
          <>
            <button onClick={() => updateStatus("arrived")} className="min-h-[44px] px-5 py-2.5 bg-purple-600 text-white text-base font-bold rounded-xl active:scale-95 transition-transform">
              Arrived
            </button>
            <button onClick={() => updateStatus("seated")} className="min-h-[44px] px-5 py-2.5 bg-teal-600 text-white text-base font-bold rounded-xl active:scale-95 transition-transform">
              Seated
            </button>
            <button onClick={() => updateStatus("cancelled")} className="min-h-[44px] px-4 py-2.5 bg-gray-100 text-gray-700 text-base font-medium rounded-xl active:scale-95 transition-transform">
              Cancel
            </button>
          </>
        )}
        {status === "arrived" && (
          <button onClick={() => updateStatus("seated")} className="min-h-[44px] px-5 py-2.5 bg-teal-600 text-white text-base font-bold rounded-xl active:scale-95 transition-transform">
            Seated
          </button>
        )}
        {(status === "seated" || status === "arrived") && (
          <button onClick={() => updateStatus("no_show")} className="min-h-[44px] px-4 py-2.5 bg-gray-100 text-gray-700 text-base font-medium rounded-xl active:scale-95 transition-transform">
            No Show
          </button>
        )}
        <button
          onClick={handleCopy}
          className={`min-h-[44px] px-4 py-2.5 rounded-xl text-base font-medium border active:scale-95 transition-all ${copied ? "bg-green-600 text-white border-green-600" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"}`}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
    </div>
  );
}
