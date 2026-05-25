export const STATUS_COLORS: Record<string, string> = {
  confirmed: "bg-blue-100 text-blue-800 border-blue-300",
  preparing: "bg-yellow-100 text-yellow-800 border-yellow-300",
  ready: "bg-green-100 text-green-800 border-green-300",
  picked_up: "bg-gray-100 text-gray-600 border-gray-300",
  cancelled: "bg-red-100 text-red-600 border-red-300",
  arrived: "bg-purple-100 text-purple-800 border-purple-300",
  seated: "bg-teal-100 text-teal-800 border-teal-300",
  no_show: "bg-orange-100 text-orange-800 border-orange-300",
};

export const STATUS_LABEL: Record<string, string> = {
  confirmed: "New",
  preparing: "Preparing",
  ready: "Ready",
  picked_up: "Picked Up",
  cancelled: "Cancelled",
  arrived: "Arrived",
  seated: "Seated",
  no_show: "No Show",
};

export const ORDER_FILTERS: { key: string; label: string }[] = [
  { key: "confirmed", label: "New" },
  { key: "preparing", label: "Preparing" },
  { key: "ready", label: "Ready" },
  { key: "all", label: "All" },
];

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function formatOrderForCopy(order: any): string {
  let text = `Order #${order.id.slice(0, 8)}\n`;
  text += `Status: ${STATUS_LABEL[order.status] || order.status}\n`;
  text += `Phone: ${order.customer_phone || "N/A"}\n`;
  text += `---\n`;
  for (const item of (order.items || [])) {
    text += `${item.quantity}x ${item.name} @ $${(item.price_cents / 100).toFixed(2)}\n`;
  }
  text += `---\n`;
  text += `Total: $${(order.total_cents / 100).toFixed(2)} (${order.item_count} items)\n`;
  return text;
}

export function formatReservationForCopy(r: any): string {
  let text = `Reservation: ${r.guest_name}\n`;
  text += `Time: ${r.start_time?.slice(0, 5)}\n`;
  text += `Party: ${r.party_size} guests\n`;
  text += `Phone: ${r.guest_phone}\n`;
  if (r.notes) text += `Notes: ${r.notes}\n`;
  return text;
}
