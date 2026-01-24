'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, AlertCircle, Mail, Building2, Briefcase, MapPin,
  CheckCircle2, XCircle, Link as LinkIcon, Eye, ChevronRight,
  Clock, User, FileText
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { api } from '@/lib/api'
import { ManualReview, ApplicationStatus, Application } from '@/types/api'
import {
  formatDate, formatDateTime, formatRelativeTime, formatStatusLabel,
  getStatusColor, formatConfidence, getConfidenceColor
} from '@/lib/utils'
import { toast } from 'sonner'
import { ProtectedRoute } from '@/components/ProtectedRoute'

type ResolveAction = 'create_new' | 'link_to_existing' | 'ignore'

function ManualReviewContent() {
  const router = useRouter()
  const queryClient = useQueryClient()

  const [selectedReview, setSelectedReview] = useState<ManualReview | null>(null)
  const [resolveAction, setResolveAction] = useState<ResolveAction>('create_new')
  const [linkToAppId, setLinkToAppId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({
    company_name: '',
    job_title: '',
    location: '',
    current_status: ApplicationStatus.APPLIED_RECEIVED,
  })

  // Fetch pending reviews
  const { data: reviewsData, isLoading } = useQuery({
    queryKey: ['manualReviews', false],
    queryFn: () => api.listManualReviews({ reviewed: false, limit: 100 }),
  })

  // Fetch applications for linking
  const { data: applicationsData } = useQuery({
    queryKey: ['applications', 'for-linking'],
    queryFn: () => api.listApplications({ limit: 100 }),
  })

  // Resolve mutation
  const resolveMutation = useMutation({
    mutationFn: (params: { id: number; action: ResolveAction; data?: any }) =>
      api.resolveManualReview(params.id, {
        action: params.action,
        ...(params.action === 'create_new' ? {
          company_name: editForm.company_name,
          job_title: editForm.job_title,
          location: editForm.location || undefined,
          current_status: editForm.current_status,
        } : {}),
        ...(params.action === 'link_to_existing' && linkToAppId ? {
          application_id: linkToAppId,
        } : {}),
      }),
    onSuccess: (data) => {
      toast.success(data.message || 'Review resolved successfully')
      queryClient.invalidateQueries({ queryKey: ['manualReviews'] })
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setSelectedReview(null)
      resetForm()
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to resolve review')
    },
  })

  const resetForm = () => {
    setResolveAction('create_new')
    setLinkToAppId(null)
    setEditForm({
      company_name: '',
      job_title: '',
      location: '',
      current_status: ApplicationStatus.APPLIED_RECEIVED,
    })
  }

  const handleSelectReview = (review: ManualReview) => {
    setSelectedReview(review)
    setEditForm({
      company_name: review.suggested_company || '',
      job_title: review.suggested_job_title || '',
      location: '',
      current_status: review.suggested_status || ApplicationStatus.APPLIED_RECEIVED,
    })
    setResolveAction('create_new')
    setLinkToAppId(null)
  }

  const handleResolve = () => {
    if (!selectedReview) return

    if (resolveAction === 'create_new' && (!editForm.company_name || !editForm.job_title)) {
      toast.error('Please fill in company name and job title')
      return
    }

    if (resolveAction === 'link_to_existing' && !linkToAppId) {
      toast.error('Please select an application to link to')
      return
    }

    resolveMutation.mutate({
      id: selectedReview.id,
      action: resolveAction,
    })
  }

  const reviews = reviewsData?.data || []
  const applications = applicationsData?.data || []

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-foreground-muted/10 bg-background-secondary/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" onClick={() => router.push('/dashboard')}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center">
                <AlertCircle className="w-6 h-6 mr-2 text-orange-400" />
                Manual Review Queue
              </h1>
              <p className="text-sm text-foreground-muted">
                {reviews.length} item{reviews.length !== 1 ? 's' : ''} needing attention
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
          </div>
        ) : reviews.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Card className="p-12 text-center max-w-lg mx-auto">
              <CheckCircle2 className="w-20 h-20 mx-auto mb-4 text-green-400" />
              <h2 className="text-2xl font-semibold mb-2">All Caught Up!</h2>
              <p className="text-foreground-muted mb-6">
                No items need manual review. All emails have been processed automatically.
              </p>
              <Button onClick={() => router.push('/dashboard')}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Card>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Reviews List */}
            <div>
              <h2 className="text-lg font-semibold mb-4">Pending Reviews</h2>
              <div className="space-y-4">
                <AnimatePresence>
                  {reviews.map((review, index) => (
                    <motion.div
                      key={review.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, x: -100 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <Card
                        glass
                        hover
                        className={`p-5 cursor-pointer transition-all ${
                          selectedReview?.id === review.id
                            ? 'ring-2 ring-primary-500'
                            : ''
                        }`}
                        onClick={() => handleSelectReview(review)}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-1">
                              <Mail className="w-4 h-4 text-foreground-muted" />
                              <span className="text-sm text-foreground-muted">
                                {review.raw_email?.from || 'Unknown sender'}
                              </span>
                            </div>
                            <h3 className="font-medium line-clamp-1">
                              {review.raw_email?.subject || 'No subject'}
                            </h3>
                          </div>
                          <Badge variant="warning" className="ml-2">
                            {formatConfidence(review.confidence)}
                          </Badge>
                        </div>

                        <div className="text-sm text-foreground-muted mb-3 line-clamp-2">
                          {review.raw_email?.body_preview || 'No preview available'}
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4 text-xs text-foreground-muted">
                            <span className="flex items-center">
                              <Clock className="w-3 h-3 mr-1" />
                              {review.raw_email
                                ? formatRelativeTime(review.raw_email.received)
                                : 'Unknown'}
                            </span>
                          </div>
                          <Badge variant="info" className="text-xs">
                            {review.reason}
                          </Badge>
                        </div>

                        {/* Suggestions */}
                        {(review.suggested_company || review.suggested_job_title) && (
                          <div className="mt-3 pt-3 border-t border-foreground-muted/10">
                            <p className="text-xs text-foreground-muted mb-2">AI Suggestions:</p>
                            <div className="flex flex-wrap gap-2">
                              {review.suggested_company && (
                                <span className="text-xs px-2 py-1 bg-primary-500/20 rounded">
                                  <Building2 className="w-3 h-3 inline mr-1" />
                                  {review.suggested_company}
                                </span>
                              )}
                              {review.suggested_job_title && (
                                <span className="text-xs px-2 py-1 bg-accent-500/20 rounded">
                                  <Briefcase className="w-3 h-3 inline mr-1" />
                                  {review.suggested_job_title}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </Card>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>

            {/* Resolution Panel */}
            <div className="lg:sticky lg:top-24 lg:self-start">
              {selectedReview ? (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                >
                  <Card glass className="p-6">
                    <h2 className="text-lg font-semibold mb-4">Resolve Review</h2>

                    {/* Email Preview */}
                    <div className="bg-background/50 rounded-lg p-4 mb-6">
                      <div className="flex items-start space-x-3">
                        <FileText className="w-5 h-5 text-foreground-muted flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium line-clamp-1">
                            {selectedReview.raw_email?.subject || 'No subject'}
                          </p>
                          <p className="text-sm text-foreground-muted mt-1">
                            From: {selectedReview.raw_email?.from || 'Unknown'}
                          </p>
                          <p className="text-sm text-foreground-muted mt-2 line-clamp-3">
                            {selectedReview.raw_email?.body_preview || 'No preview available'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Action Selection */}
                    <div className="mb-6">
                      <label className="block text-sm font-medium text-foreground-muted mb-2">
                        Choose Action
                      </label>
                      <div className="space-y-2">
                        <label className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
                          resolveAction === 'create_new'
                            ? 'border-primary-500 bg-primary-500/10'
                            : 'border-foreground-muted/20 hover:border-foreground-muted/40'
                        }`}>
                          <input
                            type="radio"
                            name="action"
                            value="create_new"
                            checked={resolveAction === 'create_new'}
                            onChange={() => setResolveAction('create_new')}
                            className="sr-only"
                          />
                          <CheckCircle2 className={`w-5 h-5 mr-3 ${
                            resolveAction === 'create_new' ? 'text-primary-500' : 'text-foreground-muted'
                          }`} />
                          <div>
                            <p className="font-medium">Create New Application</p>
                            <p className="text-xs text-foreground-muted">
                              Create a new job application from this email
                            </p>
                          </div>
                        </label>

                        <label className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
                          resolveAction === 'link_to_existing'
                            ? 'border-primary-500 bg-primary-500/10'
                            : 'border-foreground-muted/20 hover:border-foreground-muted/40'
                        }`}>
                          <input
                            type="radio"
                            name="action"
                            value="link_to_existing"
                            checked={resolveAction === 'link_to_existing'}
                            onChange={() => setResolveAction('link_to_existing')}
                            className="sr-only"
                          />
                          <LinkIcon className={`w-5 h-5 mr-3 ${
                            resolveAction === 'link_to_existing' ? 'text-primary-500' : 'text-foreground-muted'
                          }`} />
                          <div>
                            <p className="font-medium">Link to Existing</p>
                            <p className="text-xs text-foreground-muted">
                              Associate this email with an existing application
                            </p>
                          </div>
                        </label>

                        <label className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
                          resolveAction === 'ignore'
                            ? 'border-primary-500 bg-primary-500/10'
                            : 'border-foreground-muted/20 hover:border-foreground-muted/40'
                        }`}>
                          <input
                            type="radio"
                            name="action"
                            value="ignore"
                            checked={resolveAction === 'ignore'}
                            onChange={() => setResolveAction('ignore')}
                            className="sr-only"
                          />
                          <XCircle className={`w-5 h-5 mr-3 ${
                            resolveAction === 'ignore' ? 'text-primary-500' : 'text-foreground-muted'
                          }`} />
                          <div>
                            <p className="font-medium">Ignore</p>
                            <p className="text-xs text-foreground-muted">
                              This email is not job-related, skip it
                            </p>
                          </div>
                        </label>
                      </div>
                    </div>

                    {/* Create New Form */}
                    {resolveAction === 'create_new' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="space-y-4 mb-6"
                      >
                        <div>
                          <label className="block text-sm font-medium text-foreground-muted mb-1">
                            Company Name *
                          </label>
                          <input
                            type="text"
                            value={editForm.company_name}
                            onChange={(e) => setEditForm({ ...editForm, company_name: e.target.value })}
                            className="w-full px-4 py-2 bg-background border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
                            placeholder="e.g., Google"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-foreground-muted mb-1">
                            Job Title *
                          </label>
                          <input
                            type="text"
                            value={editForm.job_title}
                            onChange={(e) => setEditForm({ ...editForm, job_title: e.target.value })}
                            className="w-full px-4 py-2 bg-background border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
                            placeholder="e.g., Software Engineer"
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
                      </motion.div>
                    )}

                    {/* Link to Existing Form */}
                    {resolveAction === 'link_to_existing' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="mb-6"
                      >
                        <label className="block text-sm font-medium text-foreground-muted mb-2">
                          Select Application
                        </label>
                        <div className="max-h-60 overflow-y-auto space-y-2 border border-foreground-muted/20 rounded-lg p-2">
                          {applications.length === 0 ? (
                            <p className="text-sm text-foreground-muted text-center py-4">
                              No applications found
                            </p>
                          ) : (
                            applications.map((app) => (
                              <label
                                key={app.id}
                                className={`flex items-center p-3 rounded-lg cursor-pointer transition-colors ${
                                  linkToAppId === app.id
                                    ? 'bg-primary-500/20 border border-primary-500'
                                    : 'bg-background/50 border border-transparent hover:bg-background'
                                }`}
                              >
                                <input
                                  type="radio"
                                  name="linkApp"
                                  value={app.id}
                                  checked={linkToAppId === app.id}
                                  onChange={() => setLinkToAppId(app.id)}
                                  className="sr-only"
                                />
                                <div className="flex-1 min-w-0">
                                  <p className="font-medium line-clamp-1">{app.company_name}</p>
                                  <p className="text-sm text-foreground-muted line-clamp-1">
                                    {app.job_title}
                                  </p>
                                </div>
                                <Badge className={getStatusColor(app.current_status)}>
                                  {formatStatusLabel(app.current_status)}
                                </Badge>
                              </label>
                            ))
                          )}
                        </div>
                      </motion.div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex space-x-3">
                      <Button
                        variant="ghost"
                        className="flex-1"
                        onClick={() => {
                          setSelectedReview(null)
                          resetForm()
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        className="flex-1"
                        onClick={handleResolve}
                        isLoading={resolveMutation.isPending}
                      >
                        {resolveAction === 'create_new' && 'Create Application'}
                        {resolveAction === 'link_to_existing' && 'Link Application'}
                        {resolveAction === 'ignore' && 'Ignore Email'}
                      </Button>
                    </div>
                  </Card>
                </motion.div>
              ) : (
                <Card className="p-8 text-center">
                  <Eye className="w-12 h-12 mx-auto mb-4 text-foreground-muted opacity-50" />
                  <h3 className="text-lg font-medium mb-2">Select a Review</h3>
                  <p className="text-foreground-muted">
                    Click on an item from the list to review and resolve it
                  </p>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ManualReviewPage() {
  return (
    <ProtectedRoute>
      <ManualReviewContent />
    </ProtectedRoute>
  )
}
