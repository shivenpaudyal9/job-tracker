'use client'

import { useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Building2, Briefcase, MapPin, Calendar, Clock,
  Link as LinkIcon, ExternalLink, Edit2, Trash2, AlertCircle,
  CheckCircle2, XCircle, ChevronRight, Save, X
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { api } from '@/lib/api'
import { ApplicationStatus, ActionType } from '@/types/api'
import {
  formatDate, formatDateTime, formatRelativeTime, formatStatusLabel,
  getStatusColor, formatConfidence, getConfidenceColor
} from '@/lib/utils'
import { toast } from 'sonner'
import { ProtectedRoute } from '@/components/ProtectedRoute'

function ApplicationDetailContent() {
  const router = useRouter()
  const params = useParams()
  const queryClient = useQueryClient()
  const applicationId = Number(params.id)

  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    company_name: '',
    job_title: '',
    location: '',
    current_status: '' as ApplicationStatus,
  })

  // Fetch application details
  const { data: application, isLoading, error } = useQuery({
    queryKey: ['application', applicationId],
    queryFn: () => api.getApplication(applicationId),
    enabled: !!applicationId,
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: typeof editForm) => api.updateApplication(applicationId, data),
    onSuccess: () => {
      toast.success('Application updated successfully')
      queryClient.invalidateQueries({ queryKey: ['application', applicationId] })
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setIsEditing(false)
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update application')
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => api.deleteApplication(applicationId),
    onSuccess: () => {
      toast.success('Application deleted')
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      router.push('/dashboard')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete application')
    },
  })

  const handleEdit = () => {
    if (application) {
      setEditForm({
        company_name: application.company_name,
        job_title: application.job_title,
        location: application.location || '',
        current_status: application.current_status,
      })
      setIsEditing(true)
    }
  }

  const handleSave = () => {
    updateMutation.mutate(editForm)
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this application? This action cannot be undone.')) {
      deleteMutation.mutate()
    }
  }

  const getEventIcon = (eventType: string) => {
    if (eventType.includes('OFFER')) return <CheckCircle2 className="w-4 h-4 text-green-400" />
    if (eventType.includes('REJECTED')) return <XCircle className="w-4 h-4 text-red-400" />
    if (eventType.includes('INTERVIEW')) return <Calendar className="w-4 h-4 text-purple-400" />
    return <ChevronRight className="w-4 h-4 text-blue-400" />
  }

  const getLinkTypeIcon = (linkType: string) => {
    return <LinkIcon className="w-4 h-4" />
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  if (error || !application) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="p-8 text-center max-w-md">
          <XCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
          <h2 className="text-xl font-semibold mb-2">Application Not Found</h2>
          <p className="text-foreground-muted mb-6">
            The application you're looking for doesn't exist or has been deleted.
          </p>
          <Button onClick={() => router.push('/dashboard')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-foreground-muted/10 bg-background-secondary/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button variant="ghost" onClick={() => router.push('/dashboard')}>
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <div>
                <h1 className="text-2xl font-bold">Application Details</h1>
                <p className="text-sm text-foreground-muted">
                  Added {formatRelativeTime(application.first_seen_date)}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {!isEditing ? (
                <>
                  <Button variant="outline" onClick={handleEdit}>
                    <Edit2 className="w-4 h-4 mr-2" />
                    Edit
                  </Button>
                  <Button
                    variant="danger"
                    onClick={handleDelete}
                    isLoading={deleteMutation.isPending}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="ghost" onClick={() => setIsEditing(false)}>
                    <X className="w-4 h-4 mr-2" />
                    Cancel
                  </Button>
                  <Button onClick={handleSave} isLoading={updateMutation.isPending}>
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Application Info Card */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card glass className="p-6">
                {!isEditing ? (
                  <>
                    <div className="flex items-start justify-between mb-6">
                      <div>
                        <div className="flex items-center space-x-3 mb-2">
                          <Building2 className="w-6 h-6 text-primary-400" />
                          <h2 className="text-2xl font-bold">{application.company_name}</h2>
                        </div>
                        <div className="flex items-center space-x-2 text-foreground-muted">
                          <Briefcase className="w-4 h-4" />
                          <span className="text-lg">{application.job_title}</span>
                        </div>
                        {application.location && (
                          <div className="flex items-center space-x-2 text-foreground-muted mt-2">
                            <MapPin className="w-4 h-4" />
                            <span>{application.location}</span>
                          </div>
                        )}
                      </div>
                      <Badge className={getStatusColor(application.current_status)}>
                        {formatStatusLabel(application.current_status)}
                      </Badge>
                    </div>

                    {/* Action Required Alert */}
                    {application.action_required && (
                      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6">
                        <div className="flex items-start space-x-3">
                          <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="font-semibold text-yellow-400">Action Required</h4>
                            {application.action_type && (
                              <p className="text-sm text-foreground-secondary mt-1">
                                {formatStatusLabel(application.action_type)}
                              </p>
                            )}
                            {application.action_description && (
                              <p className="text-sm text-foreground-muted mt-1">
                                {application.action_description}
                              </p>
                            )}
                            {application.action_deadline && (
                              <p className="text-sm text-yellow-400/80 mt-2">
                                <Clock className="w-3 h-3 inline mr-1" />
                                Deadline: {formatDate(application.action_deadline)}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Details Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-background/50 rounded-lg p-4">
                        <p className="text-xs text-foreground-muted uppercase tracking-wide">First Seen</p>
                        <p className="font-medium mt-1">{formatDate(application.first_seen_date)}</p>
                      </div>
                      <div className="bg-background/50 rounded-lg p-4">
                        <p className="text-xs text-foreground-muted uppercase tracking-wide">Status Updated</p>
                        <p className="font-medium mt-1">{formatRelativeTime(application.status_updated_at)}</p>
                      </div>
                      <div className="bg-background/50 rounded-lg p-4">
                        <p className="text-xs text-foreground-muted uppercase tracking-wide">Events</p>
                        <p className="font-medium mt-1">{application.event_count}</p>
                      </div>
                      <div className="bg-background/50 rounded-lg p-4">
                        <p className="text-xs text-foreground-muted uppercase tracking-wide">Links</p>
                        <p className="font-medium mt-1">{application.link_count}</p>
                      </div>
                    </div>
                  </>
                ) : (
                  /* Edit Form */
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-foreground-muted mb-1">
                        Company Name
                      </label>
                      <input
                        type="text"
                        value={editForm.company_name}
                        onChange={(e) => setEditForm({ ...editForm, company_name: e.target.value })}
                        className="w-full px-4 py-2 bg-background border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground-muted mb-1">
                        Job Title
                      </label>
                      <input
                        type="text"
                        value={editForm.job_title}
                        onChange={(e) => setEditForm({ ...editForm, job_title: e.target.value })}
                        className="w-full px-4 py-2 bg-background border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground-muted mb-1">
                        Location
                      </label>
                      <input
                        type="text"
                        value={editForm.location}
                        onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                        className="w-full px-4 py-2 bg-background border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
                        placeholder="e.g., San Francisco, CA"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground-muted mb-1">
                        Status
                      </label>
                      <select
                        value={editForm.current_status}
                        onChange={(e) => setEditForm({ ...editForm, current_status: e.target.value as ApplicationStatus })}
                        className="w-full px-4 py-2 bg-background border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
                      >
                        {Object.values(ApplicationStatus).map((status) => (
                          <option key={status} value={status}>
                            {formatStatusLabel(status)}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
              </Card>
            </motion.div>

            {/* Timeline */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <Clock className="w-5 h-5 mr-2 text-primary-400" />
                  Activity Timeline
                </h3>

                {application.events.length === 0 ? (
                  <p className="text-foreground-muted text-center py-8">No events recorded yet</p>
                ) : (
                  <div className="relative">
                    {/* Timeline line */}
                    <div className="absolute left-4 top-0 bottom-0 w-px bg-foreground-muted/20" />

                    <div className="space-y-4">
                      {application.events.map((event, index) => (
                        <motion.div
                          key={event.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.05 }}
                          className="relative pl-10"
                        >
                          {/* Timeline dot */}
                          <div className="absolute left-2 top-1 w-4 h-4 rounded-full bg-background-secondary border-2 border-primary-500 flex items-center justify-center">
                            {getEventIcon(event.event_type)}
                          </div>

                          <div className="bg-background-secondary/50 rounded-lg p-4">
                            <div className="flex items-start justify-between">
                              <div>
                                <p className="font-medium">{formatStatusLabel(event.event_type)}</p>
                                {event.old_status && event.new_status && (
                                  <p className="text-sm text-foreground-muted mt-1">
                                    <Badge className={getStatusColor(event.old_status)}>
                                      {formatStatusLabel(event.old_status)}
                                    </Badge>
                                    <span className="mx-2">→</span>
                                    <Badge className={getStatusColor(event.new_status)}>
                                      {formatStatusLabel(event.new_status)}
                                    </Badge>
                                  </p>
                                )}
                                {event.notes && (
                                  <p className="text-sm text-foreground-muted mt-2">{event.notes}</p>
                                )}
                              </div>
                              <span className="text-xs text-foreground-muted">
                                {formatDateTime(event.event_date)}
                              </span>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            </motion.div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Confidence Scores */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
            >
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Confidence Scores</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-foreground-muted">Overall</span>
                      <span className={`font-medium ${getConfidenceColor(application.overall_confidence)}`}>
                        {formatConfidence(application.overall_confidence)}
                      </span>
                    </div>
                    <div className="h-2 bg-background rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          application.overall_confidence >= 0.9 ? 'bg-green-500' :
                          application.overall_confidence >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${application.overall_confidence * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-foreground-muted">Company</span>
                      <span className={`font-medium ${getConfidenceColor(application.company_confidence)}`}>
                        {formatConfidence(application.company_confidence)}
                      </span>
                    </div>
                    <div className="h-2 bg-background rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          application.company_confidence >= 0.9 ? 'bg-green-500' :
                          application.company_confidence >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${application.company_confidence * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-foreground-muted">Job Title</span>
                      <span className={`font-medium ${getConfidenceColor(application.job_title_confidence)}`}>
                        {formatConfidence(application.job_title_confidence)}
                      </span>
                    </div>
                    <div className="h-2 bg-background rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          application.job_title_confidence >= 0.9 ? 'bg-green-500' :
                          application.job_title_confidence >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${application.job_title_confidence * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>

            {/* Links */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <LinkIcon className="w-5 h-5 mr-2 text-primary-400" />
                  Extracted Links
                </h3>

                {application.links.length === 0 ? (
                  <p className="text-foreground-muted text-center py-4">No links extracted</p>
                ) : (
                  <div className="space-y-3">
                    {application.links.map((link) => (
                      <a
                        key={link.id}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-3 bg-background/50 rounded-lg hover:bg-background transition-colors group"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              {getLinkTypeIcon(link.link_type)}
                              <Badge variant="info" className="text-xs">
                                {formatStatusLabel(link.link_type)}
                              </Badge>
                            </div>
                            <p className="text-sm text-foreground-muted mt-1 truncate">
                              {link.link_text || link.url}
                            </p>
                          </div>
                          <ExternalLink className="w-4 h-4 text-foreground-muted group-hover:text-primary-400 transition-colors flex-shrink-0 ml-2" />
                        </div>
                      </a>
                    ))}
                  </div>
                )}
              </Card>
            </motion.div>

            {/* Metadata */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
            >
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Metadata</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-foreground-muted">Application ID</span>
                    <span className="font-mono">#{application.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-foreground-muted">Created</span>
                    <span>{formatDateTime(application.created_at)}</span>
                  </div>
                  {application.updated_at && (
                    <div className="flex justify-between">
                      <span className="text-foreground-muted">Last Updated</span>
                      <span>{formatDateTime(application.updated_at)}</span>
                    </div>
                  )}
                  {application.application_date && (
                    <div className="flex justify-between">
                      <span className="text-foreground-muted">Applied On</span>
                      <span>{formatDate(application.application_date)}</span>
                    </div>
                  )}
                </div>
              </Card>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ApplicationDetailPage() {
  return (
    <ProtectedRoute>
      <ApplicationDetailContent />
    </ProtectedRoute>
  )
}
