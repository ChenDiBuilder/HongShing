import type { LandingConfig } from "../types";

const DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_LABEL: Record<string, string> = {
  Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", Thu: "Thursday",
  Fri: "Friday", Sat: "Saturday", Sun: "Sunday",
};

// Shown across the app whenever the restaurant is outside its operating hours.
// Driven by the server-computed `is_open` (evaluated in the restaurant's own
// timezone), so it stays correct even when the box is running before open or
// after the daily stop. Renders nothing when open, or when hours are unknown
// (is_open === undefined). Width is controlled by the parent container.
export function ClosedBanner({ config }: { config: LandingConfig }) {
  if (config.is_open !== false) return null;

  const hours = config.hours_display || {};
  const days = DAY_ORDER.filter((d) => d in hours);
  const todayKey = DAY_ORDER[(new Date().getDay() + 6) % 7]; // JS Sun=0 → Mon-first index
  const closedToday = !config.hours_today || config.hours_today.trim().toLowerCase() === "closed";

  return (
    <div className="w-full mb-4 rounded-2xl border border-red-200 bg-red-50 p-4">
      <div className="flex items-center gap-2">
        <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500" />
        <p className="font-bold text-red-700">We're currently closed</p>
      </div>
      <p className="text-sm text-red-600/90 mt-1">
        {closedToday
          ? "We're closed today. You can browse the menu, but online ordering is unavailable right now."
          : `Today's hours: ${config.hours_today}. You can browse the menu, but online ordering is unavailable right now.`}
      </p>
      {days.length > 0 && (
        <div className="mt-3 rounded-xl bg-white/70 p-3">
          <p className="text-xs font-semibold text-gray-500 mb-1.5">Opening hours</p>
          <ul className="space-y-0.5 text-sm">
            {days.map((d) => (
              <li key={d} className={`flex justify-between ${d === todayKey ? "font-semibold text-gray-900" : "text-gray-600"}`}>
                <span>{DAY_LABEL[d]}</span>
                <span className={hours[d].trim().toLowerCase() === "closed" ? "text-red-500" : ""}>{hours[d]}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
