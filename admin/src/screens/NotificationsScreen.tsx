import { useState, useEffect } from "react";

export default function NotificationsScreen() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [recipientId, setRecipientId] = useState("");
  const [body, setBody] = useState("");
  const [messageType, setMessageType] = useState("marketing");
  const [sent, setSent] = useState(false);

  useEffect(() => {
    fetch("/api/admin/notifications", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setNotifications(d.data || []));
  }, []);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    setSent(false);
    const params = new URLSearchParams({ body, message_type: messageType });
    if (recipientId) params.append("recipient_id", recipientId);
    const r = await fetch(`/api/admin/notifications/sms?${params}`, {
      method: "POST",
      credentials: "include",
    });
    if (r.ok) setSent(true);
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Notifications</h1>

      <form onSubmit={handleSend} className="bg-white rounded-xl shadow-sm p-6 mb-8 space-y-4">
        <h2 className="text-lg font-semibold">Send SMS</h2>
        <input
          value={recipientId}
          onChange={(e) => setRecipientId(e.target.value)}
          placeholder="Customer ID (leave empty for broadcast)"
          className="w-full px-3 py-2 border rounded-lg"
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Message body..."
          className="w-full px-3 py-2 border rounded-lg"
          rows={3}
          required
        />
        <select value={messageType} onChange={(e) => setMessageType(e.target.value)} className="px-3 py-2 border rounded-lg">
          <option value="marketing">Marketing</option>
          <option value="transactional">Transactional</option>
        </select>
        <button type="submit" className="px-4 py-2 bg-red-600 text-white rounded-lg">Send</button>
        {sent && <span className="text-green-600 ml-4">Sent!</span>}
      </form>

      <div className="bg-white rounded-xl shadow-sm">
        <table className="w-full">
          <thead><tr className="border-b text-left text-sm text-gray-500"><th className="p-4">Body</th><th className="p-4">Type</th><th className="p-4">Channel</th><th className="p-4">Status</th><th className="p-4">Sent</th></tr></thead>
          <tbody>
            {notifications.map((n: any) => (
              <tr key={n.id} className="border-b">
                <td className="p-4 text-sm">{n.body}</td>
                <td className="p-4 text-sm">{n.message_type}</td>
                <td className="p-4 text-sm">{n.channel}</td>
                <td className="p-4">{n.status}</td>
                <td className="p-4 text-sm">{n.sent_at ? new Date(n.sent_at).toLocaleString() : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
