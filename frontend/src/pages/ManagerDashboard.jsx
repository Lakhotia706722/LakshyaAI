import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function ManagerDashboard() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In MVP, we might just reuse the existing deals endpoint and filter, 
    // or call a specific manager endpoint. For now we use the existing deals API.
    api.get('/deals')
      .then(response => {
        setDeals(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Error fetching deals:", error);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-8 text-center text-gray-400">Loading manager dashboard...</div>;

  const atRiskDeals = deals.filter(d => d.risk_flag);

  return (
    <div className="p-8 space-y-8 bg-gray-900 min-h-screen text-gray-100">
      <header>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
          Manager Dashboard
        </h1>
        <p className="text-gray-400 mt-2">Team overview and deal health.</p>
      </header>

      <section>
        <h2 className="text-xl font-semibold mb-4 border-b border-gray-800 pb-2">Deals At Risk</h2>
        {atRiskDeals.length === 0 ? (
          <p className="text-gray-500 italic">No deals currently flagged for risk.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {atRiskDeals.map(deal => (
              <div key={deal.id} className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 shadow-sm hover:shadow-md transition">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-medium text-red-200">{deal.title}</h3>
                  <span className="text-xs bg-red-500/20 text-red-300 px-2 py-1 rounded-full border border-red-500/30">
                    At Risk
                  </span>
                </div>
                <p className="text-sm text-gray-400 mb-4">Stage: <span className="capitalize text-gray-300">{deal.stage}</span></p>
                <div className="bg-black/30 p-3 rounded text-sm text-red-200/80">
                  <span className="font-semibold block mb-1">Risk Reason:</span>
                  {deal.risk_reason || "Unknown risk factor"}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4 border-b border-gray-800 pb-2">Active Pipeline</h2>
        <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-900/50 text-gray-400 border-b border-gray-700">
              <tr>
                <th className="px-6 py-4 font-medium">Deal Title</th>
                <th className="px-6 py-4 font-medium">Owner</th>
                <th className="px-6 py-4 font-medium">Stage</th>
                <th className="px-6 py-4 font-medium">Value</th>
                <th className="px-6 py-4 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {deals.map(deal => (
                <tr key={deal.id} className="hover:bg-gray-700/30 transition">
                  <td className="px-6 py-4 font-medium text-gray-200">{deal.title}</td>
                  <td className="px-6 py-4 text-gray-400">{deal.owner_name || 'Unassigned'}</td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-gray-800 border border-gray-600 text-gray-300 capitalize">
                      {deal.stage}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-400">
                    {deal.value_inr ? `₹${deal.value_inr.toLocaleString()}` : '—'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {deal.risk_flag ? (
                      <span className="text-red-400 font-medium">Risk Flagged</span>
                    ) : (
                      <span className="text-emerald-400 font-medium">Healthy</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
