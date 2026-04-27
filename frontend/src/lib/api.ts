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
  JMIStats,
  JobPosting,
  TrendingSkillsResponse,
  WeeklyReportResponse,
  MatchResponse,
  JobsListResponse,
  JobsListParams,
} from '@/types/api'

// In the browser, route through Next.js /proxy rewrite so CORS is never an issue.
// On the server (SSR), call the backend directly.
const API_BASE_URL = typeof window !== 'undefined'
  ? '/proxy'
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')

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

  // ── JMI Public APIs ────────────────────────────────────────────────────────

  async getJMIStats(): Promise<JMIStats> {
    return this.request('/api/stats')
  }

  async getWeeklyReport(): Promise<WeeklyReportResponse> {
    return this.request('/api/trends/weekly')
  }

  async getRecentJobs(params?: { role?: string; limit?: number }): Promise<{ total: number; data: JobPosting[] }> {
    const q = new URLSearchParams()
    if (params?.role) q.append('role', params.role)
    if (params?.limit) q.append('limit', String(params.limit))
    const qs = q.toString()
    return this.request(`/api/jobs/recent${qs ? `?${qs}` : ''}`)
  }

  async getTrendingSkills(window?: number): Promise<TrendingSkillsResponse> {
    const qs = window ? `?window=${window}` : ''
    return this.request(`/api/skills/trending${qs}`)
  }

  async matchResume(resumeText: string, signal?: AbortSignal): Promise<MatchResponse> {
    return this.request('/api/match', {
      method: 'POST',
      body: JSON.stringify({ resume_text: resumeText }),
      signal,
    })
  }

  async extractResume(file: File): Promise<{ text: string }> {
    const form = new FormData()
    form.append('file', file)
    const url = `${this.baseUrl}/api/extract-resume`
    const response = await fetch(url, { method: 'POST', body: form })
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Extraction failed' }))
      throw new Error(err.detail)
    }
    return response.json()
  }

  async listJobs(params: JobsListParams = {}): Promise<JobsListResponse> {
    const q = new URLSearchParams()
    if (params.search) q.append('search', params.search)
    if (params.role_category) q.append('role_category', params.role_category)
    if (params.seniority) q.append('seniority', params.seniority)
    if (params.remote_only) q.append('remote_only', 'true')
    if (params.visa_only) q.append('visa_only', 'true')
    if (params.sort) q.append('sort', params.sort)
    if (params.page) q.append('page', String(params.page))
    if (params.limit) q.append('limit', String(params.limit))
    const qs = q.toString()
    return this.request(`/api/jobs/list${qs ? `?${qs}` : ''}`)
  }
}

export const api = new ApiClient()
