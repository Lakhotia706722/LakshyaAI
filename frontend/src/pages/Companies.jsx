import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

// Redirect to CompanyGraph which is the full implementation
export default function Companies() {
  const navigate = useNavigate()
  useEffect(() => {
    navigate('/company-graph', { replace: true })
  }, [navigate])
  return null
}
