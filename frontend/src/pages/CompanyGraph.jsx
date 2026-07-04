import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

const SCORE_COLOR = (score) => {
  if (score >= 75) return 'text-green-700 bg-green-100'
  if (score >= 50) return 'text-yellow-700 bg-yellow-100'
  return 'text-red-700 bg-red-100'
}

export default function CompanyGraph() {
  const [companies, setCompanies] = useState([])
  const [filtered, setFiltered] = useState([])
  const [search, setSearch] = useState('')
  const [industryFilter, setIndustryFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')
  const [sortBy, setSortBy] = useState('growth_signal')
  const [selectedCompany, setSelectedCompany] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => { fetchCompanies() }, [])

  useEffect(() => {
    let result = [...companies]
    if (search) result = result.filter(c =>
      c.name.toLowerCase().includes(search.toLowerCase())
    )
    if (industryFilter) result = result.filter(c => c.industry === industryFilter)
    if (cityFilter) result = result.filter(c => c.city === cityFilter)
    result.sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0))
    setFiltered(result)
  }, [companies, search, industryFilter, cityFilter, sortBy])

  const fetchCompanies = async () => {
    try {
      const res = await api.get('/companies/?limit=200')
      setCompanies(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const industries = [...new Set(companies.map(c => c.industry).filter(Boolean))]
  const cities = [...new Set(companies.map(c => c.city).filter(Boolean))]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Company Intelligence Graph</h2>
          <p className="text-gray-600 mt-1">B2B company signals — financial health & growth</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 text-sm text-yellow-800">
          🎭 <strong>Demo Mode:</strong> Illustrative seed data — real version uses MCA21/GST/Udyam
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search by name..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 min-w-48 px-3 py-2 border border-gray-300 rounded-lg text-sm"
        />
        <select
          value={industryFilter}
          onChange={e => setIndustryFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Industries</option>
          {industries.map(i => <option key={i} value={i}>{i}</option>)}
        </select>
        <select
          value={cityFilter}
          onChange={e => setCityFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Cities</option>
          {cities.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="growth_signal">Sort: Growth Signal</option>
          <option value="financial_health_score">Sort: Financial Health</option>
        </select>
        <span className="self-center text-sm text-gray-500">{filtered.length} companies</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Company List */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-gray-500">Loading companies...</div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Industry</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">City</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Financial</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Growth</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filtered.map(c => (
                  <tr
                    key={c.id}
                    onClick={() => setSelectedCompany(c)}
                    className={`cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedCompany?.id === c.id ? 'bg-primary-50' : ''
                    }`}
                  >
                    <td className="px-5 py-3 text-sm font-medium text-gray-900">{c.name}</td>
                    <td className="px-5 py-3 text-sm text-gray-500">{c.industry}</td>
                    <td className="px-5 py-3 text-sm text-gray-500">{c.city}</td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${SCORE_COLOR(c.financial_health_score)}`}>
                        {c.financial_health_score ?? '—'}/100
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${SCORE_COLOR(c.growth_signal)}`}>
                        {c.growth_signal ?? '—'}/100
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Company Detail */}
        <div className="bg-white rounded-lg shadow p-5">
          {!selectedCompany ? (
            <div className="text-center text-gray-500 py-12">
              <div className="text-4xl mb-2">🏢</div>
              <p>Click a company to view details</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-bold text-gray-900">{selectedCompany.name}</h3>
                <p className="text-sm text-gray-500">{selectedCompany.industry} · {selectedCompany.city}, {selectedCompany.state}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <ScoreCard
                  label="Financial Health"
                  score={selectedCompany.financial_health_score}
                  tooltip="Computed from filing frequency, charge creation, and EPFO trends (illustrative for demo)"
                />
                <ScoreCard
                  label="Growth Signal"
                  score={selectedCompany.growth_signal}
                  tooltip="Based on job postings, GST filings, and web activity trends (illustrative for demo)"
                />
              </div>

              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Employees</p>
                <p className="text-sm text-gray-800">{selectedCompany.employee_band || '—'}</p>
              </div>

              {selectedCompany.tech_stack_tags?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Tech Stack</p>
                  <div className="flex flex-wrap gap-1">
                    {selectedCompany.tech_stack_tags.map(tag => (
                      <span key={tag} className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedCompany.gst_number && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-1">GST Number</p>
                  <p className="text-sm font-mono text-gray-700">{selectedCompany.gst_number}</p>
                </div>
              )}

              {selectedCompany.udyam_number && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Udyam Number</p>
                  <p className="text-sm font-mono text-gray-700">{selectedCompany.udyam_number}</p>
                </div>
              )}

              <div className="bg-gray-50 rounded p-3 text-xs text-gray-500 italic">
                ⓘ Scores are illustrative for demo. Production version computes these from MCA21 filings, EPFO data, GST return frequency, and public web signals.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ScoreCard({ label, score, tooltip }) {
  const color = score >= 75 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-600'
  const bg = score >= 75 ? 'bg-green-50 border-green-200' : score >= 50 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'
  return (
    <div className={`rounded-lg border p-3 ${bg}`} title={tooltip}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{score ?? '—'}<span className="text-sm text-gray-400">/100</span></p>
    </div>
  )
}
