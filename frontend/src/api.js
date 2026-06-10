// NyayaFlow API v2 - production build
import axios from 'axios'

const api = axios.create({ baseURL: `${import.meta.env.VITE_API_URL || ''}/api`, timeout: 60000 })

// Attach JWT token to every request
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('nyaya_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// Auth
export const register = (name, email, password) =>
  api.post('/auth/register', { name, email, password }).then(r => r.data)

export const login = (email, password) =>
  api.post('/auth/login', { email, password }).then(r => r.data)

export const getMe = () =>
  api.get('/auth/me').then(r => r.data.user)

// Chat
export const sendChatMessage = (query) =>
  api.post('/chat', { query }).then(r => r.data)

// Doc generation
export const getDocTypes = () =>
  api.get('/doc-types').then(r => r.data.doc_types)

export const generateDocument = (doc_type, fields) =>
  api.post('/generate-doc', { doc_type, fields }, { responseType: 'blob' })
    .then(r => {
      const url  = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      const cd   = r.headers['content-disposition'] || ''
      const name = cd.match(/filename="?([^"]+)"?/)?.[1] || 'NyayaFlow_Document.pdf'
      link.href = url; link.download = name; link.click()
      URL.revokeObjectURL(url)
      const remaining = r.headers['x-tokens-remaining']
      return { success: true, tokens_remaining: remaining ? parseInt(remaining) : null }
    })

// Voice
export const transcribeAudio = (audioBlob, ext = 'webm') => {
  const formData = new FormData()
  formData.append('audio', audioBlob, `recording.${ext}`)
  return api.post('/transcribe', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
}

// Tokens
export const getTokenBalance = () =>
  api.get('/tokens/balance').then(r => r.data)

export const getTokenPlans = () =>
  api.get('/tokens/plans').then(r => r.data)

export const createOrder = (plan_id) =>
  api.post('/tokens/order', { plan_id }).then(r => r.data)

export const verifyPayment = (payload) =>
  api.post('/tokens/verify', payload).then(r => r.data)

// History
export const getChatHistory = (limit = 50) =>
  api.get(`/history?limit=${limit}`).then(r => r.data)