/**
 * API Client for Job Tracker Backend
 */

import {
  Application,
  ApplicationDetail,
  ApplicationStatus,
  ManualReview,
  SyncStatus,
  ConnectStartResponse,
  ConnectPollResponse,
  SyncRunResponse,
  Stats,
  PaginatedResponse,
  ApiError,
} from '@/types/api'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('auth_token')
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const token = this.getAuthToken()

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...options?.headers,
        },
      })

      if (!response.ok) {
        // Handle 401 - clear token and redirect to login
        if (response.status === 401 && typeof window !== 'undefined') {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_user')
          window.location.href = '/login'
          throw new Error('Session expired. Please login again.')
        }

        const error: ApiError = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`,
        }))
        throw new Error(error.detail)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      throw new Error('An unknown error occurred')
    }
  }

  // Health & Status
  async health(): Promise<{ status: string; timestamp: string }> {
    return this.request('/health')
  }

  async getStats(): Promise<Stats> {
    return this.request('/stats')
  }

  // Sync Operations
  async getSyncStatus(): Promise<SyncStatus> {
    return this.request('/sync/status')
  }

  async startConnect(): Promise<ConnectStartResponse> {
    return this.request('/sync/connect/start', { method: 'POST' })
  }

  async pollConnect(): Promise<ConnectPollResponse> {
    return this.request('/sync/connect/poll', { method: 'POST' })
  }

  async runSync(daysBack: number = 30): Promise<SyncRunResponse> {
    return this.request(`/sync/run?days_back=${daysBack}`, { method: 'POST' })
  }

  async exportExcel(): Promise<Blob> {
    const url = `${this.baseUrl}/sync/export/excel`
    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`Failed to export: ${response.statusText}`)
    }

    return response.blob()
  }

  // Applications
  async listApplications(params?: {
    search?: string
    status?: ApplicationStatus
    company?: string
    min_confidence?: number
    action_required?: boolean
    skip?: number
    limit?: number
  }): Promise<PaginatedResponse<Application>> {
    const searchParams = new URLSearchParams()

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value))
        }
      })
    }

    const query = searchParams.toString()
    return this.request(`/applications${query ? `?${query}` : ''}`)
  }

  async getApplication(id: number): Promise<ApplicationDetail> {
    return this.request(`/applications/${id}`)
  }

  async getApplicationEvents(id: number): Promise<{ application_id: number; total: number; events: any[] }> {
    return this.request(`/applications/${id}/events`)
  }

  async createApplication(data: {
    company_name: string
    job_title: string
    location?: string
    application_date?: string
    current_status?: ApplicationStatus
  }): Promise<Application> {
    return this.request('/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateApplication(
    id: number,
    data: {
      company_name?: string
      job_title?: string
      location?: string
      current_status?: ApplicationStatus
      action_required?: boolean
      action_type?: string
      action_deadline?: string
      action_description?: string
      notes?: string
      is_archived?: boolean
    }
  ): Promise<{ id: number; message: string }> {
    return this.request(`/applications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async exportCsv(): Promise<Blob> {
    const url = `${this.baseUrl}/applications/export/csv`
    const token = this.getAuthToken()

    const response = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })

    if (!response.ok) {
      throw new Error(`Failed to export: ${response.statusText}`)
    }

    return response.blob()
  }

  async deleteApplication(id: number): Promise<{ message: string }> {
    return this.request(`/applications/${id}`, {
      method: 'DELETE',
    })
  }

  // Manual Reviews
  async listManualReviews(params?: {
    reviewed?: boolean
    skip?: number
    limit?: number
  }): Promise<PaginatedResponse<ManualReview>> {
    const searchParams = new URLSearchParams()

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value))
        }
      })
    }

    const query = searchParams.toString()
    return this.request(`/manual-reviews${query ? `?${query}` : ''}`)
  }

  async resolveManualReview(
    id: number,
    data: {
      action: 'create_new' | 'link_to_existing' | 'ignore'
      application_id?: number
      company_name?: string
      job_title?: string
      location?: string
      current_status?: ApplicationStatus
    }
  ): Promise<{ message: string; action: string; application_id?: number }> {
    return this.request(`/manual-reviews/${id}/resolve`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }
}

export const api = new ApiClient()
