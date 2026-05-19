import { useState, useEffect } from "react";

interface Customer {
  id: string;
  phone?: string;
  name?: string;
  email?: string;
  created_at: string;
}

export default function CustomersScreen() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");

  async function load() {
    const params = search ? `?search=${encodeURIComponent(search)}` : "";
    const r = await fetch(`/api/admin/customers${params}`, { credentials: "include" });
    const d = await r.json();
    setCustomers(d.data?.items || []);
  }

  useEffect(() => { load(); }, []);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Customers</h1>
      <div className="flex gap-4 mb-6">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load()}
          placeholder="Search by phone or name..."
          className="px-4 py-2 border rounded-lg flex-1"
        />
        <button onClick={load} className="px-4 py-2 bg-red-600 text-white rounded-lg">Search</button>
      </div>
      <div className="bg-white rounded-xl shadow-sm">
        <table className="w-full">
          <thead><tr className="border-b text-left text-sm text-gray-500"><th className="p-4">Phone</th><th className="p-4">Name</th><th className="p-4">Email</th><th className="p-4">Joined</th></tr></thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id} className="border-b hover:bg-gray-50 cursor-pointer">
                <td className="p-4 font-mono">{c.phone || "-"}</td>
                <td className="p-4">{c.name || "-"}</td>
                <td className="p-4 text-sm text-gray-600">{c.email || "-"}</td>
                <td className="p-4 text-sm">{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
