import { useState, useEffect } from 'react'
import { api } from '../api/client'

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi (हिंदी)' },
  { code: 'ta', label: 'Tamil (தமிழ்)' },
  { code: 'te', label: 'Telugu (తెలుగు)' },
  { code: 'mr', label: 'Marathi (मराठी)' },
  { code: 'gu', label: 'Gujarati (ગુજરાતી)' },
  { code: 'bn', label: 'Bengali (বাংলা)' },
]

export default function CallIntelligence() {
  const [recordings, setRecordings] = useState([])
  const [deals, setDeals] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [language, setLanguage] = useState('en')
  const [dealId, setDealId] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [selectedRecording, setSelectedRecording] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchRecordings()
    fetchDeals()
  }, [])

  const fetchRecordings = async () => {
    try {
      const res = await api.get('/calls/')
      setRecordings(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  const fetchDeals = async () => {
    try {
      const res = await api.get('/deals/')
      setDeals(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!selectedFile) return
    setError('')
    setIsUploading(true)

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('language', language)
    if (dealId) formData.append('deal_id', dealId)

    try {
      const res = await api.post('/calls/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setSelectedRecording(res.data)
      await fetchRecordings()
      setSelectedFile(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Check OPENAI_API_KEY.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Vernacular Call AI</h2>
          <p className="text-gray-600 mt-1">Transcribe and analyze sales calls in Indian languages</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 text-sm text-yellow-800">
          🎭 <strong>Demo Mode:</strong> Uses OpenAI Whisper (general-purpose, not fine-tuned)
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Panel */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Upload Recording</h3>
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Audio File
              </label>
              <input
                type="file"
                accept=".mp3,.wav,.m4a,.ogg,.webm"
                onChange={e => setSelectedFile(e.target.files[0])}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              {selectedFile && (
                <p className="text-xs text-green-600 mt-1">✓ {selectedFile.name}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">MP3, WAV, M4A, OGG, WebM</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <select
                value={language}
                onChange={e => setLanguage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                {LANGUAGES.map(l => (
                  <option key={l.code} value={l.code}>{l.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Link to Deal (optional)
              </label>
              <select
                value={dealId}
                onChange={e => setDealId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">-- None --</option>
                {deals.map(d => (
                  <option key={d.id} value={d.id}>{d.title}</option>
                ))}
              </select>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isUploading || !selectedFile}
              className="w-full bg-primary-600 text-white py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              {isUploading ? '🔄 Transcribing...' : '📞 Upload & Analyze'}
            </button>
          </form>

          {/* Past recordings */}
          {recordings.length > 0 && (
            <div className="mt-6 border-t pt-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Recent Recordings</h4>
              <div className="space-y-2">
                {recordings.map(r => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedRecording(r)}
                    className={`w-full text-left px-3 py-2 rounded border text-sm transition-colors ${
                      selectedRecording?.id === r.id
                        ? 'bg-primary-50 border-primary-300'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex justify-between">
                      <span className="font-medium truncate">
                        {r.file_path.split(/[/\\]/).pop()}
                      </span>
                      <span className="text-xs text-gray-500 ml-2">
                        {LANGUAGES.find(l => l.code === r.language)?.label || r.language}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {new Date(r.created_at).toLocaleDateString('en-IN')}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Analysis Panel */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedRecording && !isUploading && (
            <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
              <div className="text-4xl mb-3">📞</div>
              <p>Upload a recording or select one from the list to see analysis</p>
            </div>
          )}

          {isUploading && (
            <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
              <div className="text-4xl mb-3 animate-pulse">🎙️</div>
              <p className="font-medium">Transcribing and analyzing...</p>
              <p className="text-sm text-gray-400 mt-1">This may take 15–30 seconds</p>
            </div>
          )}

          {selectedRecording && !isUploading && (
            <>
              {/* Talk Time */}
              {selectedRecording.analysis_json?.talk_time_ratio && (
                <div className="bg-white rounded-lg shadow p-5">
                  <h4 className="font-semibold text-gray-700 mb-3">Talk Time Ratio</h4>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-600 w-16">Seller</span>
                    <div className="flex-1 bg-gray-200 rounded-full h-4 relative">
                      <div
                        className="bg-blue-500 h-4 rounded-full"
                        style={{ width: `${selectedRecording.analysis_json.talk_time_ratio.seller_pct || 50}%` }}
                      />
                    </div>
                    <span className="text-sm font-bold text-blue-700 w-10">
                      {selectedRecording.analysis_json.talk_time_ratio.seller_pct || '—'}%
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-sm text-gray-600 w-16">Buyer</span>
                    <div className="flex-1 bg-gray-200 rounded-full h-4">
                      <div
                        className="bg-green-500 h-4 rounded-full"
                        style={{ width: `${selectedRecording.analysis_json.talk_time_ratio.buyer_pct || 50}%` }}
                      />
                    </div>
                    <span className="text-sm font-bold text-green-700 w-10">
                      {selectedRecording.analysis_json.talk_time_ratio.buyer_pct || '—'}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    ⓘ {selectedRecording.analysis_json.talk_time_ratio.note}
                  </p>
                </div>
              )}

              {/* Coaching Notes */}
              {selectedRecording.analysis_json?.coaching_notes?.length > 0 && (
                <div className="bg-white rounded-lg shadow p-5">
                  <h4 className="font-semibold text-gray-700 mb-3">💡 Coaching Notes</h4>
                  <div className="space-y-2">
                    {selectedRecording.analysis_json.coaching_notes.map((note, i) => (
                      <div key={i} className="flex items-start bg-amber-50 border border-amber-200 rounded p-3">
                        <span className="text-amber-500 mr-2 mt-0.5">●</span>
                        <p className="text-gray-800 text-sm">{note}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Objections + Competitors side by side */}
              <div className="grid grid-cols-2 gap-4">
                {selectedRecording.analysis_json?.objections?.length > 0 && (
                  <div className="bg-white rounded-lg shadow p-5">
                    <h4 className="font-semibold text-gray-700 mb-3">Objections</h4>
                    <ul className="space-y-1">
                      {selectedRecording.analysis_json.objections.map((o, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start">
                          <span className="text-red-500 mr-2">•</span>{o}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {selectedRecording.analysis_json?.competitor_mentions?.length > 0 && (
                  <div className="bg-white rounded-lg shadow p-5">
                    <h4 className="font-semibold text-gray-700 mb-3">Competitors</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedRecording.analysis_json.competitor_mentions.map((c, i) => (
                        <span key={i} className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Summary */}
              {selectedRecording.analysis_json?.summary && (
                <div className="bg-white rounded-lg shadow p-5">
                  <h4 className="font-semibold text-gray-700 mb-2">Summary</h4>
                  <p className="text-gray-800 text-sm">{selectedRecording.analysis_json.summary}</p>
                </div>
              )}

              {/* Transcript */}
              {selectedRecording.transcript && (
                <div className="bg-white rounded-lg shadow p-5">
                  <h4 className="font-semibold text-gray-700 mb-3">Transcript</h4>
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-4 rounded-lg max-h-64 overflow-y-auto font-sans">
                    {selectedRecording.transcript}
                  </pre>
                </div>
              )}

              {/* Error state */}
              {selectedRecording.analysis_json?.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
                  <strong>Error:</strong> {selectedRecording.analysis_json.error}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
