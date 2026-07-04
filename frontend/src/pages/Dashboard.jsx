import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'

const STAGE_COLORS = {
  prospecting: '#94a3b8',
  demo: '#60a5fa',
  proposal: '#fbbf24',
  negotiation: '#f97316',
  closed_won: '#22c55e',
  closed_lost: '#ef4444',
}

const STAGE_LABELS = {
  prospecting: 'Prospecting',
  demo: 'Demo',
  proposal: 'Proposal',
  negotiation: 'Negotiation',
  closed_won: 'Closed Won',
  closed_lost: 'Closed Lost',
}

const fmt = (n) => n >= 100000
  ? `₹${(n / 100000).toFixed(1)}L`
  : `₹${n?.toLocaleString('en-IN') || 0}`

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [recentRecordings, setRecentRecordings] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    Promise.all([fetchStats(), fetchForecast(), fetchRecordings()]).finally(() =>
      setIsLoading(false)
    )
  }, [])

  const fetchStats = async () => {
    const res = await api.get('/deals/dashboard')
    setStats(res.data)
  }

  const fetchForecast = async () => {
    try {
      const res = await api.get('/forecast/snapshot/latest')
      setForecast(res.data)
    } catch (err) {/* no forecast yet */}
  }

  const fetchRecordings = async () => {
    try {
      const res = await api.get('/calls/?limit=3')
      setRecentRecordings(res.data)
    } catch (err) {/* no recordings yet */}
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    )
  }

  const chartData = stats
    ? Object.entries(stats.deals_by_stage).map(([stage, count]) => ({
        name: STAGE_LABELS[stage] || stage,
        count,
        fill: STAGE_COLORS[stage] || '#94a3b8',
      }))
    : []

  const riskDeals = stats?.risk_flagged_deals || 0
  const totalPipeline = stats?.total_pipeline_value || 0
  const gapPct = forecast?.gap_pct ?? null

  return (
    <div className="space-y-6">
      {/* Top KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon="💰"
          label="Total Pipeline"
          value={fmt(totalPipeline)}
          sub="Active deals"
          color="blue"
          href="/deals"
        />
        <KpiCard
          icon="⚠️"
          label="At Risk"
          value={riskDeals}
          sub="Deals flagged"
          color={riskDeals > 0 ? 'red' : 'green'}
          href="/deals"
        />
        <KpiCard
          icon="📊"
          label="Forecast Gap"
          value={gapPct !== null ? `${gapPct}%` : '—'}
          sub="Pipeline vs invoiced"
          color={gapPct > 50 ? 'red' : gapPct > 20 ? 'yellow' : 'green'}
          href="/forecasting"
        />
        <KpiCard
          icon="🏢"
          label="Companies"
          value={stats?.top_companies?.length || 0}
          sub="In intelligence graph"
          color="purple"
          href="/company-graph"
        />
      </div>

      {/* Main row: funnel chart + risk panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Deals by Stage */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold text-gray-800">Deals by Stage</h3>
            <Link to="/deals" className="text-sm text-primary-600 hover:underline">View all →</Link>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Risk Snapshot */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold text-gray-800">⚠️ At-Risk Deals</h3>
            <Link to="/deals" className="text-sm text-primary-600 hover:underline">View all →</Link>
          </div>
          {riskDeals === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <div className="text-3xl mb-2">✅</div>
              <p className="text-sm">No deals currently flagged at risk</p>
            </div>
          ) : (
            <div className="text-center py-6">
              <p className="text-5xl font-bold text-red-600">{riskDeals}</p>
              <p className="text-gray-500 text-sm mt-2">deals need attention</p>
              <Link
                to="/deals"
                className="inline-block mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700"
              >
                Review Deals
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Bottom row: top companies + call coaching + forecast */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Companies */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold text-gray-800">Top Companies</h3>
            <Link to="/company-graph" className="text-sm text-primary-600 hover:underline">View all →</Link>
          </div>
          <div className="space-y-3">
            {(stats?.top_companies || []).map(c => (
              <div key={c.id} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">{c.name}</p>
                  <p className="text-xs text-gray-500">{c.industry} · {c.city}</p>
                </div>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                  c.growth_signal >= 75 ? 'bg-green-100 text-green-700' :
                  c.growth_signal >= 50 ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {c.growth_signal}/100
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Call Highlights */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold text-gray-800">📞 Call Coaching</h3>
            <Link to="/call-intelligence" className="text-sm text-primary-600 hover:underline">View all →</Link>
          </div>
          {recentRecordings.length === 0 ? (
            <div className="text-center text-gray-500 py-8 text-sm">
              <div className="text-3xl mb-2">📞</div>
              <p>No recordings yet</p>
              <Link to="/call-intelligence" className="text-primary-600 hover:underline mt-2 block">
                Upload a call recording →
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentRecordings.map(r => (
                <div key={r.id} className="bg-amber-50 border border-amber-200 rounded p-3">
                  <p className="text-xs font-semibold text-gray-600 mb-1">
                    {new Date(r.created_at).toLocaleDateString('en-IN')}
                  </p>
                  {r.analysis_json?.coaching_notes?.[0] && (
                    <p className="text-sm text-gray-800">
                      💡 {r.analysis_json.coaching_notes[0]}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Forecast Gap */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold text-gray-800">📈 Revenue Forecast</h3>
            <Link to="/forecasting" className="text-sm text-primary-600 hover:underline">Details →</Link>
          </div>
          {!forecast || forecast.invoiced_value_inr === 0 ? (
            <div className="text-center text-gray-500 py-6 text-sm">
              <div className="text-3xl mb-2">📊</div>
              <p>No invoice data yet</p>
              <Link to="/forecasting" className="text-primary-600 hover:underline mt-2 block">
                Upload Tally CSV →
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Pipeline</span>
                <span className="font-semibold text-blue-700">{fmt(forecast.pipeline_value_inr)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Invoiced</span>
                <span className="font-semibold text-green-700">{fmt(forecast.invoiced_value_inr)}</span>
              </div>
              <div className="border-t pt-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Gap</span>
                  <span className={`text-xl font-bold ${
                    forecast.gap_pct > 50 ? 'text-red-600' :
                    forecast.gap_pct > 20 ? 'text-yellow-600' :
                    'text-green-600'
                  }`}>
                    {forecast.gap_pct}%
                  </span>
                </div>
                {forecast.closed_won_not_invoiced?.length > 0 && (
                  <p className="text-xs text-red-600 mt-1">
                    {forecast.closed_won_not_invoiced.length} closed deals not invoiced
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function KpiCard({ icon, label, value, sub, color, href }) {
  const colors = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
    purple: 'bg-purple-500',
  }
  return (
    <Link to={href} className="bg-white rounded-lg shadow p-5 hover:shadow-md transition-shadow block">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
        <div className={`w-12 h-12 ${colors[color]} rounded-xl flex items-center justify-center text-2xl shadow`}>
          {icon}
        </div>
      </div>
    </Link>
  )
}
