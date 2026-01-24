'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { User, AuthToken, LoginRequest, RegisterRequest } from '@/types/api'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (data: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Load token from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('auth_token')
    const savedUser = localStorage.getItem('auth_user')

    if (savedToken && savedUser) {
      setToken(savedToken)
      try {
        setUser(JSON.parse(savedUser))
      } catch {
        localStorage.removeItem('auth_user')
      }
    }

    setIsLoading(false)
  }, [])

  const login = useCallback(async (data: LoginRequest) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(error.detail)
    }

    const result: AuthToken = await response.json()

    setToken(result.access_token)
    setUser(result.user)

    localStorage.setItem('auth_token', result.access_token)
    localStorage.setItem('auth_user', JSON.stringify(result.user))
  }, [])

  const register = useCallback(async (data: RegisterRequest) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Registration failed' }))
      throw new Error(error.detail)
    }

    const result = await response.json()

    setToken(result.access_token)
    setUser(result.user)

    localStorage.setItem('auth_token', result.access_token)
    localStorage.setItem('auth_user', JSON.stringify(result.user))
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
  }, [])

  const refreshUser = useCallback(async () => {
    if (!token) return

    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        const userData: User = await response.json()
        setUser(userData)
        localStorage.setItem('auth_user', JSON.stringify(userData))
      } else if (response.status === 401) {
        // Token expired
        logout()
      }
    } catch (error) {
      console.error('Failed to refresh user:', error)
    }
  }, [token, logout])

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token && !!user,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
