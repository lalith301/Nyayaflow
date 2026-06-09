import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getMe } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem('nyaya_token')
    if (!token) { setLoading(false); return }
    try {
      const u = await getMe()
      setUser(u)
    } catch {
      localStorage.removeItem('nyaya_token')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadUser() }, [loadUser])

  const signIn = (token, userData) => {
    localStorage.setItem('nyaya_token', token)
    setUser(userData)
  }

  const signOut = () => {
    localStorage.removeItem('nyaya_token')
    setUser(null)
  }

  const updateTokens = (newBalance) => {
    setUser(prev => prev ? { ...prev, tokens: newBalance } : prev)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut, updateTokens, reload: loadUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)