import { useState, useEffect } from 'react'
import { api } from '../api/client'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, Cell
} from 'recharts'

const fmt = (n) => n >= 100000
  ? `₹${(n / 100000).toFixed(1)}L`
  : `₹${n.toLocaleString('en-IN')}`

export default function Forecasting() {
  const [snapshot, setSnapshot] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => { fetchSnapshot() }, [])

  const fetchSnapshot = async () => {
    try {
      const res = await api.get('/forecast/snapshot/latest')
      setSnapshot(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownloadTemplate = async () => {
    try {
      const res = await api.get('/forecast/sample-csv-template', { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = 'tally_invoice_template.csv'
      a.click()
    } catch (err) {
      console.error(err)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return
    setError('')
    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await api.post('/forecast/upload-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setResult(res.data)
      await fetchSnapshot()
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const chartData = snapshot
    ? [
        { name: 'Pipeline', value: snapshot.pipeline_value_inr, fill: '#3b82f6' },
        { name: 'Invoiced', value: snapshot.invoiced_value_inr, fill: '#10b981' },
      ]
    : []

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Revenue Forecasting</h2>
          <p className="text-gray-600 mt-1">Pipeline vs invoiced — reconcile with Tally exports</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 text-sm text-yellow-800">
          🎭 <strong>Demo Mode:</strong> CSV upload simulation — real version requires Tally API
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Panel */}
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h3 className="font-semibold text-gray-800">Import Tally Invoices</h3>

          <button
            onClick={handleDownloadTemplate}
            className="w-full text-sm text-primary-600 border border-primary-300 py-2 rounded-lg hover:bg-primary-50"
          >
            ⬇ Download CSV Template
          </button>

          <form onSubmit={handleUpload} className="space-y-3">
            <input
              type="file"
              accept=".csv"
              onChange={e => setFile(e.target.files[0])}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2"
            />
            {file && <p className="text-xs text-green-600">✓ {file.name}</p>}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isUploading || !file}
              className="w-full bg-primary-600 text-white py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm"
            >
              {isUploading ? '🔄 Processing...' : '📊 Upload & Reconcile'}
            </button>
          </form>

          {result && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm space-y-1">
              <p className="font-semibold text-green-800">✓ Import complete</p>
              <p className="text-green-700">Matched: {result.matched_invoices} invoices</p>
              {result.unmatched_rows?.length > 0 && (
                <p className="text-yellow-700">Unmatched: {result.unmatched_rows.join(', ')}</p>
              )}
            </div>
          )}
        </div>

        {/* KPI Cards + Chart */}
        <div className="lg:col-span-2 space-y-4">
          {isLoading ? (
            <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">Loading forecast...</div>
          ) : (
            <>
              {/* KPI row */}
              <div className="grid grid-cols-3 gap-4">
                <KpiCard label="Total Pipeline" value={fmt(snapshot?.pipeline_value_inr || 0)} color="blue" />
                <KpiCard label="Invoiced" value={fmt(snapshot?.invoiced_value_inr || 0)} color="green" />
                <KpiCard
                  label="Gap"
                  value={`${snapshot?.gap_pct ?? 100}%`}
                  color={snapshot?.gap_pct > 50 ? 'red' : snapshot?.gap_pct > 20 ? 'yellow' : 'green'}
                  sub="pipeline vs invoiced"
                />
              </div>

              {/* Bar chart */}
              <div className="bg-white rounded-lg shadow p-5">
                <h3 className="font-semibold text-gray-700 mb-4">Pipeline vs Invoiced</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={chartData} barCategoryGap="40%">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis tickFormatter={v => `₹${(v / 100000).toFixed(0)}L`} />
                    <Tooltip formatter={v => fmt(v)} />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                {snapshot?.notes && (
                  <p className="text-xs text-gray-400 mt-2">{snapshot.notes}</p>
                )}
              </div>

              {/* Unmatched closed-won deals */}
              {snapshot?.closed_won_not_invoiced?.length > 0 && (
                <div className="bg-white rounded-lg shadow p-5">
                  <h3 className="font-semibold text-gray-700 mb-3">
                    ⚠️ Closed Won — No Invoice Found ({snapshot.closed_won_not_invoiced.length})
                  </h3>
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Deal</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {snapshot.closed_won_not_invoiced.map(d => (
                        <tr key={d.deal_id} className="hover:bg-gray-50">
                          <td className="px-4 py-2 text-gray-900">{d.title}</td>
                          <td className="px-4 py-2 text-gray-500">{d.company}</td>
                          <td className="px-4 py-2 font-medium text-red-700">{fmt(d.value_inr || 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function KpiCard({ label, value, color, sub }) {
  const colors = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    red: 'bg-red-50 border-red-200 text-red-700',
  }
  return (
    <div className={`rounded-lg border p-4 ${colors[color]}`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}
