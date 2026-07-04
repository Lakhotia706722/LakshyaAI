import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function WhatsAppIntelligence() {
  const [conversationText, setConversationText] = useState('')
  const [deals, setDeals] = useState([])
  const [companies, setCompanies] = useState([])
  const [selectedDealId, setSelectedDealId] = useState('')
  const [createNewDeal, setCreateNewDeal] = useState(false)
  const [newDealTitle, setNewDealTitle] = useState('')
  const [newDealCompanyId, setNewDealCompanyId] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [intelligence, setIntelligence] = useState(null)
  const [error, setError] = useState('')
  const [uploadFile, setUploadFile] = useState(null)

  useEffect(() => {
    fetchDeals()
    fetchCompanies()
  }, [])

  const fetchDeals = async () => {
    try {
      const response = await api.get('/deals/')
      setDeals(response.data)
    } catch (err) {
      console.error('Failed to fetch deals:', err)
    }
  }

  const fetchCompanies = async () => {
    try {
      const response = await api.get('/companies/')
      setCompanies(response.data)
    } catch (err) {
      console.error('Failed to fetch companies:', err)
    }
  }

  const handleAnalyze = async (e) => {
    e.preventDefault()
    setError('')
    setIntelligence(null)
    setIsAnalyzing(true)

    try {
      const formData = new FormData()
      
      if (uploadFile) {
        formData.append('file', uploadFile)
      } else {
        formData.append('conversation_text', conversationText)
      }
      
      if (selectedDealId) {
        formData.append('deal_id', selectedDealId)
      }
      
      if (createNewDeal) {
        formData.append('create_new_deal', 'true')
        formData.append('new_deal_title', newDealTitle)
        formData.append('new_deal_company_id', newDealCompanyId)
      }

      const endpoint = uploadFile ? '/whatsapp/upload' : '/whatsapp/analyze'
      const response = await api.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      setIntelligence(response.data.intelligence)
      
      // Refresh deals if new one was created
      if (createNewDeal) {
        fetchDeals()
        setCreateNewDeal(false)
        setNewDealTitle('')
        setNewDealCompanyId('')
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to analyze conversation. Make sure ANTHROPIC_API_KEY is set.'
      setError(errorMsg)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      setUploadFile(file)
      // Clear text input when file is selected
      setConversationText('')
    }
  }

  const exampleConversation = `[06/01/24, 10:15:23] Rajesh Kumar: Hi, this is Rajesh from TechVision Solutions. Thanks for connecting!
[06/01/24, 10:16:45] Priya Sharma: Hi Rajesh! Yes, we're interested in your CRM solution. Can you tell me more about pricing?
[06/01/24, 10:18:12] Rajesh Kumar: Absolutely! Our pricing starts at ₹50,000/month for up to 50 users. This includes all core features.
[06/01/24, 10:20:33] Priya Sharma: That's a bit higher than what we budgeted. We're currently using Salesforce, which is ₹30,000/month.
[06/01/24, 10:22:15] Rajesh Kumar: I understand. Let me schedule a demo for next week so you can see the value. How does Tuesday 3 PM work?
[06/01/24, 10:24:50] Priya Sharma: Tuesday works, but I'll need to check with my CFO first about the budget.
[06/01/24, 10:25:30] Rajesh Kumar: Perfect! I'll send you a calendar invite. Also, what are your main pain points with Salesforce?`

  const loadExample = () => {
    setConversationText(exampleConversation)
    setUploadFile(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">WhatsApp Deal Intelligence</h2>
          <p className="text-gray-600 mt-1">Extract structured insights from WhatsApp conversations</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2">
          <p className="text-yellow-800 text-sm flex items-center">
            <span className="mr-2">🎭</span>
            <span><strong>Demo Mode:</strong> Using paste/upload simulation</span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Input Conversation</h3>
          
          <form onSubmit={handleAnalyze} className="space-y-4">
            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Upload WhatsApp Export (.txt)
              </label>
              <input
                type="file"
                accept=".txt"
                onChange={handleFileChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              {uploadFile && (
                <p className="text-sm text-green-600 mt-1">✓ {uploadFile.name}</p>
              )}
            </div>

            <div className="text-center text-gray-500 text-sm">OR</div>

            {/* Text Input */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Paste Conversation
                </label>
                <button
                  type="button"
                  onClick={loadExample}
                  className="text-sm text-primary-600 hover:text-primary-700"
                >
                  Load Example
                </button>
              </div>
              <textarea
                value={conversationText}
                onChange={(e) => {
                  setConversationText(e.target.value)
                  setUploadFile(null)
                }}
                rows={10}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                placeholder="[DD/MM/YY, HH:MM:SS] Sender: Message&#10;[DD/MM/YY, HH:MM:SS] Sender: Message..."
              />
            </div>

            {/* Deal Linking Options */}
            <div className="border-t pt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Link to Deal (Optional)
              </label>
              
              {!createNewDeal ? (
                <>
                  <select
                    value={selectedDealId}
                    onChange={(e) => setSelectedDealId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-2"
                  >
                    <option value="">-- Select Existing Deal --</option>
                    {deals.map((deal) => (
                      <option key={deal.id} value={deal.id}>
                        {deal.title} ({deal.company?.name})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setCreateNewDeal(true)}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    + Create New Deal Instead
                  </button>
                </>
              ) : (
                <div className="space-y-3 bg-gray-50 p-3 rounded">
                  <input
                    type="text"
                    value={newDealTitle}
                    onChange={(e) => setNewDealTitle(e.target.value)}
                    placeholder="Deal Title"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    required={createNewDeal}
                  />
                  <select
                    value={newDealCompanyId}
                    onChange={(e) => setNewDealCompanyId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    required={createNewDeal}
                  >
                    <option value="">-- Select Company --</option>
                    {companies.map((company) => (
                      <option key={company.id} value={company.id}>
                        {company.name} ({company.city})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => {
                      setCreateNewDeal(false)
                      setNewDealTitle('')
                      setNewDealCompanyId('')
                    }}
                    className="text-sm text-gray-600 hover:text-gray-700"
                  >
                    ← Back to Select Existing
                  </button>
                </div>
              )}
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isAnalyzing || (!conversationText && !uploadFile)}
              className="w-full bg-primary-600 text-white py-3 px-4 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isAnalyzing ? '🔄 Analyzing with Claude AI...' : '🤖 Analyze with AI'}
            </button>
          </form>
        </div>

        {/* Results Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Intelligence Extracted</h3>
          
          {!intelligence && !isAnalyzing && (
            <div className="text-center text-gray-500 py-12">
              <div className="text-4xl mb-2">💬</div>
              <p>Paste or upload a conversation and click "Analyze with AI"</p>
            </div>
          )}

          {isAnalyzing && (
            <div className="text-center text-gray-500 py-12">
              <div className="text-4xl mb-2 animate-pulse">🤖</div>
              <p>Claude AI is analyzing the conversation...</p>
            </div>
          )}

          {intelligence && (
            <div className="space-y-4">
              {/* Deal Stage */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Deal Stage</h4>
                <span className="inline-block px-3 py-1 bg-blue-600 text-white rounded-full text-sm font-medium capitalize">
                  {intelligence.stage.replace('_', ' ')}
                </span>
              </div>

              {/* Summary */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Summary</h4>
                <p className="text-gray-800">{intelligence.summary}</p>
              </div>

              {/* Key Insights */}
              {intelligence.key_insights && intelligence.key_insights.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Key Insights</h4>
                  <ul className="list-disc list-inside space-y-1">
                    {intelligence.key_insights.map((insight, idx) => (
                      <li key={idx} className="text-gray-700">{insight}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Next Steps */}
              {intelligence.next_steps && intelligence.next_steps.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Next Steps</h4>
                  <div className="space-y-2">
                    {intelligence.next_steps.map((step, idx) => (
                      <div key={idx} className="flex items-start bg-green-50 border border-green-200 rounded p-3">
                        <span className="text-green-600 mr-2">✓</span>
                        <div className="flex-1">
                          <p className="text-gray-800 font-medium">{step.action}</p>
                          <div className="flex gap-3 text-xs text-gray-600 mt-1">
                            <span>👤 {step.owner || 'Unassigned'}</span>
                            {step.deadline && <span>📅 {step.deadline}</span>}
                            <span className={`px-2 py-0.5 rounded ${
                              step.priority === 'high' ? 'bg-red-100 text-red-700' :
                              step.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {step.priority}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Risk Signals */}
              {intelligence.risk_signals && intelligence.risk_signals.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">⚠️ Risk Signals</h4>
                  <div className="space-y-2">
                    {intelligence.risk_signals.map((risk, idx) => (
                      <div key={idx} className={`border-l-4 p-3 rounded ${
                        risk.severity === 'high' ? 'bg-red-50 border-red-500' :
                        risk.severity === 'medium' ? 'bg-yellow-50 border-yellow-500' :
                        'bg-gray-50 border-gray-500'
                      }`}>
                        <div className="flex justify-between items-start">
                          <p className="text-gray-800">{risk.description}</p>
                          <span className="text-xs font-semibold uppercase ml-2">{risk.severity}</span>
                        </div>
                        <p className="text-xs text-gray-600 mt-1">{risk.type}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Objections */}
              {intelligence.objections && intelligence.objections.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Objections Raised</h4>
                  <ul className="space-y-1">
                    {intelligence.objections.map((objection, idx) => (
                      <li key={idx} className="text-gray-700 flex items-start">
                        <span className="text-red-500 mr-2">•</span>
                        {objection}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Competitor Mentions */}
              {intelligence.competitor_mentions && intelligence.competitor_mentions.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Competitors Mentioned</h4>
                  <div className="flex flex-wrap gap-2">
                    {intelligence.competitor_mentions.map((competitor, idx) => (
                      <span key={idx} className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">
                        {competitor}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Sentiment Trajectory */}
              {intelligence.sentiment_trajectory && intelligence.sentiment_trajectory.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Sentiment Trajectory</h4>
                  <div className="space-y-2">
                    {intelligence.sentiment_trajectory.map((sentiment, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <span className="text-xs text-gray-600 w-20">{sentiment.timestamp}</span>
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${
                              sentiment.score > 0.3 ? 'bg-green-500' :
                              sentiment.score < -0.3 ? 'bg-red-500' :
                              'bg-yellow-500'
                            }`}
                            style={{ width: `${((sentiment.score + 1) / 2) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600">{sentiment.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
