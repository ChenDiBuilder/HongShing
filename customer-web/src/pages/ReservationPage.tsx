import { useState, useEffect } from "react";
import { api } from "../context/api";
import { getLandingConfig, type LandingConfigResponse } from "../lib/api";

export function ReservationPage({ primaryColor: _primaryColor, setPage: _setPage, profile }: any) {
  const [date, setDate] = useState("");
  const [party, setParty] = useState(2);
  const [notes, setNotes] = useState("");
  const [slots, setSlots] = useState<any[]>([]);
  const [booked, setBooked] = useState(false);
  const [myRes, setMyRes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (profile) {
      fetch(api("/api/customer/me/reservations"), { credentials: "include" })
        .then((r) => r.json()).then((d) => setMyRes(d.reservations || [])).catch(() => {});
    }
  }, [profile]);

  async function checkSlots() {
    if (!date) return; setSlots([]);
    try {
      const r = await fetch(api(`/api/reservations/slots?reservation_date=${date}&party_size=${party}`));
      const d = await r.json();
      setSlots(d.slots || []);
    } catch {}
  }

  async function book(slot: any) {
    if (!profile) return;
    setLoading(true);
    try {
      const r = await fetch(api("/api/reservations"), {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ reservation_date: date, start_time: slot.start_time, party_size: party, notes: notes || null }),
      });
      if (r.ok) { setBooked(true); setMyRes((await fetch(api("/api/customer/me/reservations"), { credentials: "include" }).then((r) => r.json())).reservations || []); }
    } catch {} finally { setLoading(false); }
  }

  if (booked) return (
    <div className="bg-white rounded-2xl shadow p-8 text-center">
      <p className="text-4xl mb-2">&#10003;</p>
      <h2 className="text-xl font-bold mb-2">Reservation Confirmed</h2>
      <p className="text-gray-500 mb-4">Your table has been booked.</p>
      <button onClick={() => { setBooked(false); setSlots([]); }} className="px-6 py-2 bg-gray-900 text-white rounded-lg">Make Another</button>
    </div>
  );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Make a Reservation</h1>
      <div className="bg-white rounded-2xl shadow p-6 mb-6 space-y-4">
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Date</label><input type="date" value={date} onChange={(e) => { setDate(e.target.value); setSlots([]); }} className="w-full px-3 py-2 border rounded-lg" min={new Date().toISOString().slice(0, 10)} /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Party Size</label><select value={party} onChange={(e) => setParty(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg">{[1,2,3,4,5,6,7,8].map((n) => <option key={n} value={n}>{n} {n === 1 ? "guest" : "guests"}</option>)}</select></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Special Requests</label><input value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full px-3 py-2 border rounded-lg" placeholder="Allergies, special occasions..." /></div>
        <button onClick={checkSlots} disabled={!date} className="w-full py-2 bg-gray-900 text-white font-semibold rounded-lg disabled:opacity-50">Check Availability</button>
      </div>
      {slots.length > 0 && (
        <div className="bg-white rounded-2xl shadow overflow-hidden mb-6">
          <h2 className="px-6 py-3 font-semibold border-b">Available Slots</h2>
          <div className="divide-y">
            {slots.map((s: any) => (
              <div key={s.id} className="px-6 py-4 flex items-center justify-between">
                <div><p className="font-semibold">{s.start_time?.slice(0, 5)} - {s.end_time?.slice(0, 5)}</p><p className="text-sm text-gray-500">{s.available_spots} table{s.available_spots !== 1 ? "s" : ""} available</p></div>
                <button onClick={() => book(s)} disabled={s.available_spots === 0 || loading} className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg disabled:opacity-50">Book</button>
              </div>
            ))}
          </div>
        </div>
      )}
      {slots.length === 0 && date && <p className="text-center text-gray-500 py-4">No slots available for this date.</p>}
      {myRes.length > 0 && (
        <div className="bg-white rounded-2xl shadow overflow-hidden">
          <h2 className="px-6 py-3 font-semibold border-b">My Reservations</h2>
          <div className="divide-y">
            {myRes.map((r: any) => (
              <div key={r.id} className="px-6 py-3 flex justify-between items-center">
                <div><p className="font-medium">{r.date} at {r.start_time?.slice(0, 5)}</p><p className="text-sm text-gray-500">{r.party_size} guests</p></div>
                <span className={`text-xs px-2 py-1 rounded-full ${r.status === "confirmed" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}>{r.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function useLandingConfig() {
  const [config, setConfig] = useState<LandingConfigResponse | null>(null);
  useEffect(() => {
    const source = new URLSearchParams(window.location.search).get("source") || undefined;
    getLandingConfig(source).then(setConfig).catch(() => {});
  }, []);
  return config;
}

function contactSentence(config: LandingConfigResponse | null) {
  const parts = [config?.support_phone, config?.privacy_contact_email].filter(Boolean);
  if (parts.length === 0) return "us";
  return parts.join(" or ");
}

export function TermsPage() {
  const config = useLandingConfig();
  return (
    <div className="bg-white rounded-2xl shadow p-8 prose prose-sm max-w-none">
      <h1 className="text-2xl font-bold mb-6">Terms and Conditions</h1>
      <p className="mb-4">By accessing this website, you agree to be bound by these terms and conditions.</p>
      <h3 className="font-bold mt-6 mb-2">Orders & Payment</h3>
      <p className="mb-4">All orders are subject to availability. Prices are in CAD and include applicable taxes. Payment is due at the time of pickup.</p>
      <h3 className="font-bold mt-6 mb-2">Pickup</h3>
      <p className="mb-4">Orders must be picked up at the designated time. We reserve the right to cancel orders not picked up within 30 minutes of the scheduled time.</p>
      <h3 className="font-bold mt-6 mb-2">Contact</h3>
      <p>For any questions, contact {contactSentence(config)}.</p>
    </div>
  );
}

export function PrivacyPage() {
  const config = useLandingConfig();
  return (
    <div className="bg-white rounded-2xl shadow p-8 prose prose-sm max-w-none">
      <h1 className="text-2xl font-bold mb-6">Privacy Policy</h1>
      <p className="mb-4">{config?.restaurant_name || "This restaurant"} takes your privacy seriously. We collect your phone number to provide rewards and order confirmations.</p>
      <p className="mb-4">Your data is not shared with third parties. You can request deletion of your data at any time by contacting us.</p>
      <p>For questions about this policy, contact {contactSentence(config)}.</p>
    </div>
  );
}
