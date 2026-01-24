/**
 * API Types for Job Tracker
 */

export enum ApplicationStatus {
  APPLIED_RECEIVED = 'APPLIED_RECEIVED',
  UNDER_REVIEW = 'UNDER_REVIEW',
  INTERVIEW_SCHEDULED = 'INTERVIEW_SCHEDULED',
  INTERVIEW_COMPLETED = 'INTERVIEW_COMPLETED',
  NEXT_STEP_ASSESSMENT = 'NEXT_STEP_ASSESSMENT',
  OFFER_RECEIVED = 'OFFER_RECEIVED',
  REJECTED = 'REJECTED',
  WITHDRAWN = 'WITHDRAWN',
  OTHER_UPDATE = 'OTHER_UPDATE',
}

export enum ActionType {
  SCHEDULE_INTERVIEW = 'SCHEDULE_INTERVIEW',
  COMPLETE_ASSESSMENT = 'COMPLETE_ASSESSMENT',
  SUBMIT_DOCUMENTS = 'SUBMIT_DOCUMENTS',
  RESPOND_TO_EMAIL = 'RESPOND_TO_EMAIL',
  FOLLOW_UP = 'FOLLOW_UP',
  OTHER = 'OTHER',
}

export interface Application {
  id: number
  company_name: string
  job_title: string
  location: string | null
  current_status: ApplicationStatus
  application_date: string | null
  first_seen_date: string
  status_updated_at: string
  action_required: boolean
  action_type: ActionType | null
  action_deadline: string | null
  action_description: string | null
  overall_confidence: number
  company_confidence: number
  job_title_confidence: number
  event_count: number
  link_count: number
  notes: string | null
  is_archived: boolean
  created_at: string
  updated_at: string | null
}

export interface ApplicationDetail extends Application {
  events: ApplicationEvent[]
  links: Link[]
}

export interface ApplicationEvent {
  id: number
  event_type: string
  event_date: string
  old_status: ApplicationStatus | null
  new_status: ApplicationStatus | null
  notes: string | null
  created_at: string
}

export interface Link {
  id: number
  url: string
  link_type: string
  link_text: string | null
  confidence: number
  created_at: string
}

export interface ManualReview {
  id: number
  reason: string
  confidence: number
  suggested_company: string | null
  suggested_job_title: string | null
  suggested_status: ApplicationStatus | null
  reviewed: boolean
  created_at: string
  raw_email: {
    id: number
    subject: string
    from: string
    received: string
    body_preview: string | null
  } | null
}

export interface SyncStatus {
  is_connected: boolean
  is_running: boolean
  last_sync_at: string | null
  last_sync_counts: {
    emails_fetched: number
    emails_processed: number
    applications_created: number
    errors_count: number
  } | null
}

export interface ConnectStartResponse {
  verification_uri: string
  user_code: string
  expires_in: number
  interval: number
  message: string
}

export interface ConnectPollResponse {
  connected: boolean
  message: string
  error: string | null
}

export interface SyncRunResponse {
  success: boolean
  message: string
  emails_fetched: number
  emails_processed: number
  applications_created: number
  applications_updated: number
  errors_count: number
}

export interface Stats {
  total_applications: number
  pending_actions: number
  pending_manual_review: number
  by_status: Record<string, number>
  recent_applications: Application[]
  last_sync: {
    completed_at: string
    emails_fetched: number
    emails_processed: number
    applications_created: number
    success: boolean
  } | null
}

export interface PaginatedResponse<T> {
  total: number
  skip: number
  limit: number
  data: T[]
}

export interface ApiError {
  detail: string
}

// Auth types
export interface User {
  id: number
  email: string
  name: string | null
  is_outlook_connected: boolean
  created_at: string
}

export interface AuthToken {
  access_token: string
  token_type: string
  user: User
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  name?: string
}
