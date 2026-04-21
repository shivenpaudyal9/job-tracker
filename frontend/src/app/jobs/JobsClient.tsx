'use client'

import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Search, Filter, X, Briefcase, Wifi, Globe, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { JobCard, JobCardSkeleton } from '@/components/JobCard'
import { api } from '@/lib/api'
import { JobsListParams } from '@/types/api'
import Link from 'next/link'

const ROLE_OPTIONS = [
  { value: '', label: 'All Roles' },
  { value: 'ml_engineer', label: 'ML Engineer' },
  { value: 'data_scientist', label: 'Data Scientist' },
  { value: 'mlops', label: 'MLOps' },
  { value: 'applied_scientist', label: 'Applied Scientist' },
  { value: 'analytics', label: 'Analytics' },
  { value: 'research', label: 'Research' },
]

const SENIORITY_OPTIONS = [
  { value: '', label: 'All Levels' },
  { value: 'intern', label: 'Intern' },
  { value: 'junior', label: 'Junior' },
  { value: 'mid', label: 'Mid' },
  { value: 'senior', label: 'Senior' },
  { value: 'staff', label: 'Staff' },
  { value: 'principal', label: 'Principal' },
]

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest' },
  { value: 'salary_desc', label: 'Salary: High to Low' },
]

function DataSourceBadge({ source, label }: { source: string; label: string }) {
  const dot = source === 'live'
    ? 'bg-green-400'
    : source === 'hybrid'
    ? 'bg-yellow-400'
    : 'bg-blue-400'
  return (
    <div className="flex items-center gap-1.5 text-xs text-foreground-muted px-3 py-1.5 rounded-full bg-foreground-muted/5 border border-foreground-muted/10">
      <span className={`w-1.5 h-1.5 rounded-full ${dot} animate-pulse`} />
      {label}
    </div>
  )
}

export default function JobsPageClient() {
  const [params, setParams] = useState<JobsListParams>({ page: 1, limit: 20, sort: 'newest' })
  const [search, setSearch] = useState('')
  const [allJobs, setAllJobs] = useState<any[]>([])
  const [loadedPages, setLoadedPages] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [dataSource, setDataSource] = useState<{ source: string; label: string } | null>(null)

  const queryParams = { ...params, search: search || undefined }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['jobs-list', queryParams],
    queryFn: async () => {
      const res = await api.listJobs(queryParams)
      if (queryParams.page === 1) {
        setAllJobs(res.jobs)
      } else {
        setAllJobs(prev => [...prev, ...res.jobs])
      }
      setHasMore(res.has_more)
      setDataSource({ source: res.data_source, label: res.label })
      return res
    },
    placeholderData: (prev: any) => prev,
  })

  const applyFilters = useCallback((newParams: Partial<JobsListParams>) => {
    setAllJobs([])
    setLoadedPages(1)
    setParams(p => ({ ...p, ...newParams, page: 1 }))
  }, [])

  const resetFilters = () => {
    setSearch('')
    setAllJobs([])
    setLoadedPages(1)
    setParams({ page: 1, limit: 20, sort: 'newest' })
  }

  const loadMore = () => {
    const next = loadedPages + 1
    setLoadedPages(next)
    setParams(p => ({ ...p, page: next }))
  }

  const totalDisplay = (data as any)?.total ? (data as any).total.toLocaleString() : '...'
  const hasFilters = !!(search || params.role_category || params.seniority || params.remote_only || params.visa_only)

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-secondary to-background">
      {/* bg blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent-600/8 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 container mx-auto px-4 sm:px-6 py-8 max-w-5xl">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Briefcase className="w-5 h-5 text-primary-400" />
                <h1 className="text-2xl font-bold">ML/DS Job Board</h1>
              </div>
              <p className="text-foreground-secondary text-sm">
                {totalDisplay} roles from 75+ top companies
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {dataSource && <DataSourceBadge {...dataSource} />}
              <Link href="/trends" className="text-xs text-primary-400 hover:underline flex items-center gap-1">
                <TrendingUp className="w-3 h-3" />Market trends
              </Link>
            </div>
          </div>
        </motion.div>

        {/* Filters */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card glass className="mb-6 p-4">
            <div className="flex flex-col gap-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
                <input
                  type="text"
                  placeholder="Search by company, role, or skill..."
                  value={search}
                  onChange={e => {
                    setSearch(e.target.value)
                    applyFilters({})
                  }}
                  className="w-full pl-9 pr-4 py-2.5 bg-background border border-foreground-muted/20 rounded-lg text-sm focus:outline-none focus:border-primary-500/50 text-foreground placeholder:text-foreground-muted"
                />
                {search && (
                  <button onClick={() => { setSearch(''); applyFilters({}) }} className="absolute right-3 top-1/2 -translate-y-1/2">
                    <X className="w-4 h-4 text-foreground-muted hover:text-foreground" />
                  </button>
                )}
              </div>

              {/* Filter row */}
              <div className="flex flex-wrap gap-2">
                <select
                  value={params.role_category || ''}
                  onChange={e => applyFilters({ role_category: e.target.value || undefined })}
                  className="px-3 py-2 bg-background border border-foreground-muted/20 rounded-lg text-sm text-foreground focus:outline-none focus:border-primary-500/50 cursor-pointer"
                >
                  {ROLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>

                <select
                  value={params.seniority || ''}
                  onChange={e => applyFilters({ seniority: e.target.value || undefined })}
                  className="px-3 py-2 bg-background border border-foreground-muted/20 rounded-lg text-sm text-foreground focus:outline-none focus:border-primary-500/50 cursor-pointer"
                >
                  {SENIORITY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>

                <select
                  value={params.sort || 'newest'}
                  onChange={e => applyFilters({ sort: e.target.value as any })}
                  className="px-3 py-2 bg-background border border-foreground-muted/20 rounded-lg text-sm text-foreground focus:outline-none focus:border-primary-500/50 cursor-pointer"
                >
                  {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>

                <button
                  onClick={() => applyFilters({ remote_only: !params.remote_only })}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm transition-colors ${
                    params.remote_only
                      ? 'bg-teal-500/20 border-teal-500/40 text-teal-300'
                      : 'bg-background border-foreground-muted/20 text-foreground-secondary hover:border-foreground-muted/40'
                  }`}
                >
                  <Wifi className="w-3.5 h-3.5" />Remote
                </button>

                <button
                  onClick={() => applyFilters({ visa_only: !params.visa_only })}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm transition-colors ${
                    params.visa_only
                      ? 'bg-green-500/20 border-green-500/40 text-green-300'
                      : 'bg-background border-foreground-muted/20 text-foreground-secondary hover:border-foreground-muted/40'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />Visa Sponsorship
                </button>

                {hasFilters && (
                  <button onClick={resetFilters} className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm text-foreground-muted hover:text-foreground transition-colors">
                    <X className="w-3.5 h-3.5" />Reset
                  </button>
                )}
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Job list */}
        <div className="space-y-3">
          {isLoading && params.page === 1 ? (
            Array.from({ length: 8 }).map((_, i) => <JobCardSkeleton key={i} />)
          ) : allJobs.length === 0 ? (
            <div className="text-center py-16">
              <Briefcase className="w-10 h-10 text-foreground-muted mx-auto mb-3" />
              <p className="text-foreground-secondary">No jobs match your filters.</p>
              <button onClick={resetFilters} className="mt-3 text-primary-400 text-sm hover:underline">
                Reset filters
              </button>
            </div>
          ) : (
            <>
              {allJobs.map((job, i) => (
                <motion.div
                  key={`${job.id}-${i}`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.03, 0.3) }}
                >
                  <JobCard job={job} />
                </motion.div>
              ))}

              {hasMore && (
                <div className="flex justify-center pt-4">
                  <Button
                    onClick={loadMore}
                    variant="outline"
                    disabled={isFetching}
                  >
                    {isFetching ? 'Loading...' : 'Load More Jobs'}
                  </Button>
                </div>
              )}

              {isFetching && params.page && params.page > 1 && (
                Array.from({ length: 3 }).map((_, i) => <JobCardSkeleton key={`sk-${i}`} />)
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-16 pt-8 border-t border-foreground-muted/10 text-center text-foreground-muted text-sm">
          <p>
            Built by{' '}
            <a href="https://portfolioneo-two.vercel.app" target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline">
              Shiven Paudyal
            </a>
            {' '}· MS CS at CSULB · Powered by FastAPI, Next.js, and Groq LLM
          </p>
        </footer>
      </div>
    </div>
  )
}
