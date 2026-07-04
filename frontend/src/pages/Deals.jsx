import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

const STAGE_STYLES = {
  prospecting: 'bg-gray-100 text-gray-700',
  demo: 'bg-blue-100 text-blue-700',
  proposal: 'bg-yellow-100 text-yellow-700',
  negotiation: 'bg-orange-100 text-orange-700',
  closed_won: 'bg-green-100 text-green-700',
  closed_lost: 'bg-red-100 text-red-700',
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

export default function Deals() {
  const [deals, setDeals] = useState([])
  const [filtered, setFiltered] = useState([])
  const [stageFilter, setStageFilter] = useState('')
  const [riskFilter, setRiskFilter] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => { fetchDeals() }, [])

  useEffect(() => {
    let result = [...deals]
    if (stageFilter) result = result.filter(d => d.stage === stageFilter)
    if (riskFilter) result = result.filter(d => d.risk_flag)
    setFiltered(result)
  }, [deals, stageFilter, riskFilter])

  const fetchDeals = async () => {
    try {
      const res = await api.get('/deals/?limit=100')
      setDeals(res.data)
    } catch (err) {
      setError('Failed to load deals')
    } finally {
      setIsLoading(false)
    }
  }

  const totalPipeline = filtered.reduce((sum, d) => sum + (d.value_inr || 0), 0)
  const riskCount = deals.filter(d => d.risk_flag).length

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Loading deals...</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">All Deals</h2>
          <p className="text-gray-600 mt-1">{filtered.length} deals · pipeline {fmt(totalPipeline)}</p>
        </div>
        {riskCount > 0 && (
          <button
            onClick={() => setRiskFilter(!riskFilter)}
            className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              riskFilter
                ? 'bg-red-600 text-white'
                : 'bg-red-50 text-red-700 border border-red-200 hover:bg-red-100'
            }`}
          >
            ⚠️ {riskFilter ? 'Show All' : `Show At-Risk (${riskCount})`}
          </button>
        )}
      </div>

      {/* Stage filter pills */}
      <div className="flex flex-wrap gap-2">
        {['', ...Object.keys(STAGE_LABELS)].map(stage => (
          <button
            key={stage}
            onClick={() => setStageFilter(stage)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              stageFilter === stage
                ? 'bg-primary-600 text-white'
                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {stage ? STAGE_LABELS[stage] : 'All Stages'}
            {stage && (
              <span className="ml-1.5 text-xs opacity-75">
                ({deals.filter(d => d.stage === stage).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>
      )}

      {/* Deals table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Deal</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stage</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Flags</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map(deal => (
              <tr key={deal.id} className={`hover:bg-gray-50 ${deal.risk_flag ? 'bg-red-50' : ''}`}>
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-gray-900">{deal.title}</div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {deal.company?.name || '—'}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${STAGE_STYLES[deal.stage]}`}>
                    {STAGE_LABELS[deal.stage]}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">
                  {deal.value_inr ? fmt(deal.value_inr) : '—'}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{deal.owner_name || '—'}</td>
                <td className="px-6 py-4">
                  {deal.risk_flag && (
                    <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-800"
                      title={deal.risk_reason || 'Risk flagged'}>
                      ⚠️ At Risk
                    </span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <Link
                    to={`/whatsapp-intelligence`}
                    className="text-xs text-primary-600 hover:underline"
                    title="Analyze WhatsApp conversation for this deal"
                  >
                    Analyze →
                  </Link>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                  No deals found for the selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
