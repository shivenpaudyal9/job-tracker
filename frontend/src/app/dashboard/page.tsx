'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Briefcase, RefreshCw, Download, Search, Filter, AlertCircle,
  TrendingUp, CheckCircle2, Clock, XCircle, Eye, LayoutGrid, LayoutList, LogOut,
  Edit2, Trash2, Archive, Moon, Sun, FileText, X, Save
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { api } from '@/lib/api'
import { Application, ApplicationStatus } from '@/types/api'
import { formatDate, formatRelativeTime, formatStatusLabel, getStatusColor, formatConfidence, getConfidenceColor, downloadBlob } from '@/lib/utils'
import { toast } from 'sonner'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { useAuth } from '@/contexts/AuthContext'

function DashboardContent() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { user, logout } = useAuth()

  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | 'all'>('all')
  const [actionFilter, setActionFilter] = useState<boolean | 'all'>('all')
  const [minConfidence, setMinConfidence] = useState<number>(0)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [isSyncing, setIsSyncing] = useState(false)
  const [darkMode, setDarkMode] = useState(false)
  const [editingApp, setEditingApp] = useState<Application | null>(null)
  const [editForm, setEditForm] = useState({ company_name: '', job_title: '', notes: '' })

  // Dark mode effect
  useEffect(() => {
    const saved = localStorage.getItem('darkMode')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches

    // Default to dark mode or use saved preference
    if (saved === 'true' || (saved === null && prefersDark)) {
      setDarkMode(true)
      document.documentElement.classList.add('dark')
    } else if (saved === 'false') {
      setDarkMode(false)
      document.documentElement.classList.remove('dark')
    } else {
      // Default to dark mode for this app
      setDarkMode(true)
      document.documentElement.classList.add('dark')
    }
  }, [])

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode
    setDarkMode(newDarkMode)
    if (newDarkMode) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('darkMode', 'true')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('darkMode', 'false')
    }
  }

  // Queries
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
  })

  const { data: syncStatus } = useQuery({
    queryKey: ['syncStatus'],
    queryFn: () => api.getSyncStatus(),
    refetchInterval: 5000, // Poll every 5 seconds
  })

  const { data: applicationsData, isLoading: appsLoading, refetch: refetchApps } = useQuery({
    queryKey: ['applications', searchQuery, statusFilter, actionFilter, minConfidence],
    queryFn: () =>
      api.listApplications({
        search: searchQuery || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        action_required: actionFilter !== 'all' ? actionFilter : undefined,
        min_confidence: minConfidence > 0 ? minConfidence : undefined,
        limit: 100,
      }),
  })

  const { data: manualReviews } = useQuery({
    queryKey: ['manualReviews'],
    queryFn: () => api.listManualReviews({ reviewed: false }),
  })

  // Mutations
  const syncMutation = useMutation({
    mutationFn: () => api.runSync(30),
    onSuccess: () => {
      toast.success('Sync started! Processing emails...')
      setIsSyncing(true)
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to start sync')
    },
  })

  const exportMutation = useMutation({
    mutationFn: () => api.exportExcel(),
    onSuccess: (blob) => {
      downloadBlob(blob, 'job_applications.xlsx')
      toast.success('Excel file downloaded!')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to export')
    },
  })

  const exportCsvMutation = useMutation({
    mutationFn: () => api.exportCsv(),
    onSuccess: (blob) => {
      downloadBlob(blob, 'job_applications.csv')
      toast.success('CSV file downloaded!')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to export CSV')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteApplication(id),
    onSuccess: () => {
      toast.success('Application deleted')
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => api.updateApplication(id, data),
    onSuccess: () => {
      toast.success('Application updated')
      setEditingApp(null)
      queryClient.invalidateQueries({ queryKey: ['applications'] })
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update')
    },
  })

  const archiveMutation = useMutation({
    mutationFn: (id: number) => api.updateApplication(id, { is_archived: true }),
    onSuccess: () => {
      toast.success('Application archived')
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to archive')
    },
  })

  const handleEdit = (app: Application) => {
    setEditingApp(app)
    setEditForm({
      company_name: app.company_name,
      job_title: app.job_title,
      notes: app.notes || ''
    })
  }

  const handleSaveEdit = () => {
    if (editingApp) {
      updateMutation.mutate({
        id: editingApp.id,
        data: editForm
      })
    }
  }

  const handleDelete = (app: Application) => {
    if (confirm(`Delete application for ${app.company_name} - ${app.job_title}?`)) {
      deleteMutation.mutate(app.id)
    }
  }

  // Effects - only redirect to setup after syncStatus has loaded
  useEffect(() => {
    if (syncStatus !== undefined && !syncStatus.is_connected) {
      router.push('/setup')
    }
  }, [syncStatus, router])

  useEffect(() => {
    if (syncStatus?.is_running) {
      setIsSyncing(true)
    } else if (isSyncing) {
      setIsSyncing(false)
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      toast.success('Sync completed!')
    }
  }, [syncStatus?.is_running])

  const applications = applicationsData?.data || []
  const pendingReviews = manualReviews?.total || 0

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-foreground-muted/10 bg-background-secondary/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Briefcase className="w-8 h-8 text-primary-400" />
              <div>
                <h1 className="text-2xl font-bold">Job Tracker</h1>
                <p className="text-sm text-foreground-muted">
                  {syncStatus?.last_sync_at
                    ? `Last synced ${formatRelativeTime(syncStatus.last_sync_at)}`
                    : 'Not synced yet'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {pendingReviews > 0 && (
                <Button
                  variant="outline"
                  onClick={() => router.push('/manual-review')}
                >
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {pendingReviews} Reviews
                  <Badge variant="warning" className="ml-2">{pendingReviews}</Badge>
                </Button>
              )}

              <Button
                variant="outline"
                onClick={() => exportCsvMutation.mutate()}
                isLoading={exportCsvMutation.isPending}
                title="Export to CSV"
              >
                <FileText className="w-4 h-4 mr-2" />
                CSV
              </Button>

              <Button
                onClick={() => syncMutation.mutate()}
                isLoading={isSyncing || syncMutation.isPending}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
                Sync Now
              </Button>

              <Button
                variant="ghost"
                onClick={toggleDarkMode}
                title="Toggle dark mode"
              >
                {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </Button>

              <Button
                variant="ghost"
                onClick={() => {
                  logout()
                  router.push('/')
                }}
                title={user?.email || 'Logout'}
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        {/* Stats Cards */}
        {!statsLoading && stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card glass hover className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-foreground-muted">Total Applications</p>
                    <p className="text-3xl font-bold mt-1">{stats.total_applications}</p>
                  </div>
                  <TrendingUp className="w-10 h-10 text-primary-400 opacity-50" />
                </div>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card glass hover className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-foreground-muted">Pending Actions</p>
                    <p className="text-3xl font-bold mt-1 text-yellow-400">{stats.pending_actions}</p>
                  </div>
                  <Clock className="w-10 h-10 text-yellow-400 opacity-50" />
                </div>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card glass hover className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-foreground-muted">Manual Reviews</p>
                    <p className="text-3xl font-bold mt-1 text-orange-400">{stats.pending_manual_review}</p>
                  </div>
                  <AlertCircle className="w-10 h-10 text-orange-400 opacity-50" />
                </div>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card glass hover className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-foreground-muted">Success Rate</p>
                    <p className="text-3xl font-bold mt-1 text-green-400">
                      {stats.total_applications > 0
                        ? Math.round((stats.by_status['OFFER_RECEIVED'] || 0) / stats.total_applications * 100)
                        : 0}%
                    </p>
                  </div>
                  <CheckCircle2 className="w-10 h-10 text-green-400 opacity-50" />
                </div>
              </Card>
            </motion.div>
          </div>
        )}

        {/* Filters & Search */}
        <Card className="p-6 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-foreground-muted" />
                <input
                  type="text"
                  placeholder="Search company or job title..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-background-secondary border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
                />
              </div>
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="px-4 py-2 bg-background-secondary border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
            >
              <option value="all">All Statuses</option>
              {Object.values(ApplicationStatus).map((status) => (
                <option key={status} value={status}>
                  {formatStatusLabel(status)}
                </option>
              ))}
            </select>

            {/* Action Filter */}
            <select
              value={String(actionFilter)}
              onChange={(e) => setActionFilter(e.target.value === 'all' ? 'all' : e.target.value === 'true')}
              className="px-4 py-2 bg-background-secondary border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
            >
              <option value="all">All Items</option>
              <option value="true">Action Required</option>
              <option value="false">No Action</option>
            </select>

            {/* View Mode */}
            <div className="flex items-center space-x-2 bg-background-secondary border border-foreground-muted/20 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded ${viewMode === 'grid' ? 'bg-primary-500 text-white' : 'text-foreground-muted hover:text-foreground'}`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded ${viewMode === 'list' ? 'bg-primary-500 text-white' : 'text-foreground-muted hover:text-foreground'}`}
              >
                <LayoutList className="w-4 h-4" />
              </button>
            </div>
          </div>
        </Card>

        {/* Applications List/Grid */}
        {appsLoading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 animate-spin text-primary-400" />
          </div>
        ) : applications.length === 0 ? (
          <Card className="p-12 text-center">
            <Briefcase className="w-16 h-16 mx-auto mb-4 text-foreground-muted opacity-50" />
            <h3 className="text-xl font-semibold mb-2">No Applications Found</h3>
            <p className="text-foreground-muted mb-6">
              {searchQuery || statusFilter !== 'all' || actionFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'Run a sync to fetch your job emails'}
            </p>
            {!searchQuery && statusFilter === 'all' && actionFilter === 'all' && (
              <Button onClick={() => syncMutation.mutate()}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Sync Now
              </Button>
            )}
          </Card>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {applications.map((app, index) => (
              <motion.div
                key={app.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Card
                  glass
                  hover
                  className="p-6 cursor-pointer h-full"
                  onClick={() => router.push(`/applications/${app.id}`)}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg mb-1 line-clamp-1">{app.company_name}</h3>
                      <p className="text-foreground-muted text-sm line-clamp-1">{app.job_title}</p>
                    </div>
                    {app.action_required && (
                      <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 ml-2" />
                    )}
                  </div>

                  <div className="space-y-3">
                    <Badge className={getStatusColor(app.current_status)}>
                      {formatStatusLabel(app.current_status)}
                    </Badge>

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-foreground-muted">Confidence</span>
                      <span className={`font-medium ${getConfidenceColor(app.overall_confidence)}`}>
                        {formatConfidence(app.overall_confidence)}
                      </span>
                    </div>

                    {app.location && (
                      <div className="text-sm text-foreground-muted">
                        📍 {app.location}
                      </div>
                    )}

                    <div className="text-xs text-foreground-muted pt-2 border-t border-foreground-muted/10">
                      {formatDate(app.first_seen_date)}
                    </div>
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>
        ) : (
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-background-secondary border-b border-foreground-muted/10">
                  <tr>
                    <th className="text-left px-6 py-4 text-sm font-medium">Company</th>
                    <th className="text-left px-6 py-4 text-sm font-medium">Job Title</th>
                    <th className="text-left px-6 py-4 text-sm font-medium">Status</th>
                    <th className="text-left px-6 py-4 text-sm font-medium">Confidence</th>
                    <th className="text-left px-6 py-4 text-sm font-medium">Date</th>
                    <th className="text-left px-6 py-4 text-sm font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {applications.map((app, index) => (
                    <motion.tr
                      key={app.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: index * 0.02 }}
                      className="border-b border-foreground-muted/10 hover:bg-background-secondary/50 transition-colors cursor-pointer"
                      onClick={() => router.push(`/applications/${app.id}`)}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-2">
                          {app.action_required && (
                            <AlertCircle className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                          )}
                          <span className="font-medium">{app.company_name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-foreground-secondary">{app.job_title}</td>
                      <td className="px-6 py-4">
                        <Badge className={getStatusColor(app.current_status)}>
                          {formatStatusLabel(app.current_status)}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        <span className={getConfidenceColor(app.overall_confidence)}>
                          {formatConfidence(app.overall_confidence)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-foreground-muted">
                        {formatDate(app.first_seen_date)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation()
                              router.push(`/applications/${app.id}`)
                            }}
                            title="View"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleEdit(app)
                            }}
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation()
                              archiveMutation.mutate(app.id)
                            }}
                            title="Archive"
                          >
                            <Archive className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-red-400 hover:text-red-300"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDelete(app)
                            }}
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Edit Modal */}
        {editingApp && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <Card className="w-full max-w-lg p-6 m-4">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">Edit Application</h2>
                <Button variant="ghost" size="sm" onClick={() => setEditingApp(null)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Company Name</label>
                  <input
                    type="text"
                    value={editForm.company_name}
                    onChange={(e) => setEditForm({ ...editForm, company_name: e.target.value })}
                    className="w-full px-4 py-2 bg-background-secondary border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Job Title</label>
                  <input
                    type="text"
                    value={editForm.job_title}
                    onChange={(e) => setEditForm({ ...editForm, job_title: e.target.value })}
                    className="w-full px-4 py-2 bg-background-secondary border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Notes</label>
                  <textarea
                    value={editForm.notes}
                    onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                    rows={4}
                    placeholder="Add your personal notes here..."
                    className="w-full px-4 py-2 bg-background-secondary border border-foreground-muted/20 rounded-lg focus:outline-none focus:border-primary-500 resize-none"
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-4">
                  <Button variant="outline" onClick={() => setEditingApp(null)}>
                    Cancel
                  </Button>
                  <Button onClick={handleSaveEdit} isLoading={updateMutation.isPending}>
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  )
}
