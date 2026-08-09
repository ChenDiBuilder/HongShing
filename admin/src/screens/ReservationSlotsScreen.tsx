import { useState, useEffect } from "react";

const apiBase = import.meta.env.VITE_API_BASE ?? "";

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

interface Slot {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  max_party_size: number;
  max_reservations: number;
  is_active: boolean;
}

interface Props { showToast: (msg: string, type?: "success" | "error") => void; }

export default function ReservationSlotsScreen({ showToast }: Props) {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [dayOfWeek, setDayOfWeek] = useState(1);
  const [startTime, setStartTime] = useState("11:00");
  const [endTime, setEndTime] = useState("11:30");
  const [maxPartySize, setMaxPartySize] = useState(6);
  const [maxReservations, setMaxReservations] = useState(4);

  useEffect(() => {
    loadSlots();
  }, []);

  async function loadSlots() {
    const r = await fetch(`${apiBase}/api/admin/reservation-slots`, { credentials: "include" });
    const d = await r.json();
    setSlots(d.data || []);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const r = await fetch(`${apiBase}/api/admin/reservation-slots`, {
      method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
      body: JSON.stringify({ day_of_week: dayOfWeek, start_time: startTime, end_time: endTime, max_party_size: maxPartySize, max_reservations: maxReservations }),
    });
    if (r.ok) { loadSlots(); showToast("Slot added!", "success"); }
    else showToast("Failed to add slot", "error");
  }

  async function handleDelete(id: string) {
    await fetch(`${apiBase}/api/admin/reservation-slots/${id}`, { method: "DELETE", credentials: "include" });
    loadSlots(); showToast("Slot removed", "success");
  }

  const grouped: Record<number, Slot[]> = {};
  for (const s of slots) {
    if (!grouped[s.day_of_week]) grouped[s.day_of_week] = [];
    grouped[s.day_of_week].push(s);
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Reservation Slots</h1>

      <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-8 space-y-4">
        <h2 className="text-lg font-semibold">Add Slot</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Day</label>
            <select value={dayOfWeek} onChange={(e) => setDayOfWeek(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg">
              {DAYS.map((d, i) => <option key={i} value={i}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start</label>
            <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} className="w-full px-3 py-2 border rounded-lg" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">End</label>
            <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} className="w-full px-3 py-2 border rounded-lg" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Party</label>
            <input type="number" value={maxPartySize} onChange={(e) => setMaxPartySize(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg" min={1} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Bookings</label>
            <input type="number" value={maxReservations} onChange={(e) => setMaxReservations(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg" min={1} />
          </div>
        </div>
        <button type="submit" className="px-4 py-2 bg-red-600 text-white rounded-lg">Add Slot</button>
      </form>

      {slots.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400">
          No reservation slots yet — add your first above.
        </div>
      )}

      {DAYS.map((day, dayIdx) => {
        const daySlots = grouped[dayIdx] || [];
        if (daySlots.length === 0) return null;
        return (
          <div key={dayIdx} className="mb-6">
            <h3 className="text-lg font-semibold mb-3">{day}</h3>
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-2 text-sm font-medium text-gray-500">Time</th>
                    <th className="text-left px-4 py-2 text-sm font-medium text-gray-500">Max Party</th>
                    <th className="text-left px-4 py-2 text-sm font-medium text-gray-500">Max Bookings</th>
                    <th className="text-right px-4 py-2 text-sm font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {daySlots.map((s) => (
                    <tr key={s.id} className="border-b last:border-0">
                      <td className="px-4 py-2">{s.start_time?.slice(0, 5)} – {s.end_time?.slice(0, 5)}</td>
                      <td className="px-4 py-2">{s.max_party_size}</td>
                      <td className="px-4 py-2">{s.max_reservations}</td>
                      <td className="px-4 py-2 text-right">
                        <button onClick={() => handleDelete(s.id)} className="text-sm text-red-600 hover:underline">Remove</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
