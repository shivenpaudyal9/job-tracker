import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow } from 'date-fns'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return format(d, 'MMM dd, yyyy')
}

export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return format(d, 'MMM dd, yyyy HH:mm')
}

export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return formatDistanceToNow(d, { addSuffix: true })
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    APPLIED_RECEIVED: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    UNDER_REVIEW: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    INTERVIEW_SCHEDULED: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    INTERVIEW_COMPLETED: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
    NEXT_STEP_ASSESSMENT: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    OFFER_RECEIVED: 'bg-green-500/20 text-green-400 border-green-500/30',
    REJECTED: 'bg-red-500/20 text-red-400 border-red-500/30',
    WITHDRAWN: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    OTHER_UPDATE: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  }

  return colors[status] || 'bg-gray-500/20 text-gray-400 border-gray-500/30'
}

export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'text-green-400'
  if (confidence >= 0.7) return 'text-yellow-400'
  return 'text-red-400'
}

export function formatStatusLabel(status: string): string {
  return status
    .split('_')
    .map(word => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ')
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}
