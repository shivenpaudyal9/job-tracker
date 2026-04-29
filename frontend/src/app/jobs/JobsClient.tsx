'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Search, X, Briefcase, ChevronDown, TrendingUp, Clock } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { JobCard, JobCardSkeleton } from '@/components/JobCard'
import { api } from '@/lib/api'
import { JobsListParams } from '@/types/api'
import Link from 'next/link'

// ── Filter options ────────────────────────────────────────────────────────────

const ROLE_OPTIONS = [
  { value: '', label: 'All Roles' },
  { value: 'ml_engineer', label: 'ML Engineer' },
  { value: 'data_scientist', label: 'Data Scientist' },
  { value: 'mlops', label: 'MLOps Engineer' },
  { value: 'applied_scientist', label: 'Applied Scientist' },
  { value: 'analytics', label: 'Analytics Engineer' },
  { value: 'research', label: 'Research Scientist' },
]

const LEVEL_OPTIONS = [
  { value: '', label: 'All Levels' },
  { value: 'entry', label: 'Entry Level' },
  { value: 'mid', label: 'Mid Level' },
  { value: 'senior', label: 'Senior Level' },
]

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest First' },
  { value: 'salary_desc', label: 'Salary: High to Low' },
]

const POSTED_WITHIN_OPTIONS = [
  { value: '', label: 'Any time' },
  { value: '4h', label: 'Last 4 hours' },
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
]

const WORK_TYPE_OPTIONS = [
  { value: '', label: 'All Locations' },
  { value: 'remote', label: 'Remote' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'onsite', label: 'Onsite' },
]

// Map simplified level → seniority values sent to backend
const LEVEL_TO_SENIORITY: Record<string, string[]> = {
  entry: ['intern', 'junior'],
  mid: ['mid'],
  senior: ['senior', 'staff', 'principal'],
}

// ── Freshness banner ──────────────────────────────────────────────────────────

function FreshnessBanner({ stats }: { stats: any }) {
  if (!stats?.last_scrape_at || stats.data_source === 'demo') return null

  const last = new Date(stats.last_scrape_at)
  const diffMs = Date.now() - last.getTime()
  const diffH = Math.floor(diffMs / 3_600_000)
  const diffM = Math.floor((diffMs % 3_600_000) / 60_000)
  const agoText = diffH >= 1 ? `${diffH}h ago` : `${diffM}m ago`

  return (
    <div className="flex items-center justify-between text-xs px-3 py-2 rounded-lg bg-foreground-muted/5 border border-foreground-muted/10 mb-4">
      <div className="flex items-center gap-1.5">
        <Clock className="w-3 h-3 text-foreground-muted" />
        <span className="text-foreground-muted">Last scrape: <span className="text-foreground-secondary">{agoText}</span></span>
      </div>
      <div className="text-foreground-muted">
        <span className="text-green-400 font-medium">{stats.jobs_last_4h ?? 0}</span> new in 4h
        {' · '}
        <span className="text-primary-400 font-medium">{stats.jobs_last_24h ?? 0}</span> today
      </div>
    </div>
  )
}

// ── Custom dropdown ───────────────────────────────────────────────────────────

interface SelectOption { value: string; label: string }

function FilterSelect({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (v: string) => void
  options: SelectOption[]
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="appearance-none pl-3 pr-8 py-2 rounded-lg border border-foreground-muted/20 text-sm hover:border-primary-500/40 focus:outline-none focus:border-primary-500/50 transition-colors whitespace-nowrap min-w-[130px] cursor-pointer"
        style={{ backgroundColor: '#1e293b', color: '#f8fafc' }}
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value} style={{ backgroundColor: '#1e293b', color: '#f8fafc' }}>
            {opt.label}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground-muted pointer-events-none" />
    </div>
  )
}

// ── Data source badge ─────────────────────────────────────────────────────────

function DataSourceBadge({ source, label }: { source: string; label: string }) {
  const dot = source === 'live' ? 'bg-green-400' : source === 'hybrid' ? 'bg-yellow-400' : 'bg-blue-400'
  return (
    <div className="flex items-center gap-1.5 text-xs text-foreground-muted px-3 py-1.5 rounded-full bg-foreground-muted/5 border border-foreground-muted/10">
      <span className={`w-1.5 h-1.5 rounded-full ${dot} animate-pulse`} />
      {label}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function JobsPageClient() {
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [level, setLevel] = useState('')
  const [sort, setSort] = useState('newest')
  const [workType, setWorkType] = useState('')
  const [visaOnly, setVisaOnly] = useState(false)
  const [entryLevel, setEntryLevel] = useState(false)
  const [postedWithin, setPostedWithin] = useState('')
  const [city, setCity] = useState('')
  const [page, setPage] = useState(1)
  const [allJobs, setAllJobs] = useState<any[]>([])
  const [hasMore, setHasMore] = useState(true)
  const [dataSource, setDataSource] = useState<{ source: string; label: string } | null>(null)

  // Map level to backend seniority param (just use first value for single-seniority filter)
  const seniorityParam = level ? LEVEL_TO_SENIORITY[level]?.[0] : undefined

  // For entry level, we'll send 'junior' but also filter client-side
  const queryParams: JobsListParams = {
    search: search || undefined,
    role_category: role || undefined,
    seniority: seniorityParam,
    remote_only: workType === 'remote' ? true : undefined,
    visa_only: visaOnly || undefined,
    entry_level: entryLevel || undefined,
    posted_within: (postedWithin || undefined) as any,
    city: city || undefined,
    sort: sort as any,
    page,
    limit: 20,
  }

  const { data: jmiStats } = useQuery({
    queryKey: ['jmi-stats'],
    queryFn: () => api.getJMIStats(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  const { isLoading, isFetching, isError } = useQuery({
    queryKey: ['jobs-list', queryParams],
    queryFn: async () => {
      const res = await api.listJobs(queryParams)
      let jobs = res.jobs

      // Client-side work type filtering
      if (workType === 'remote') {
        jobs = jobs.filter(j => j.remote && !j.location?.toLowerCase().includes('hybrid'))
      } else if (workType === 'hybrid') {
        jobs = jobs.filter(j => j.location?.toLowerCase().includes('hybrid'))
      } else if (workType === 'onsite') {
        jobs = jobs.filter(j => !j.remote && !j.location?.toLowerCase().includes('hybrid'))
      }

      // Client-side entry level filter (also include intern)
      if (level === 'entry') {
        jobs = jobs.filter(j => ['intern', 'junior'].includes(j.seniority ?? ''))
      } else if (level === 'senior') {
        jobs = jobs.filter(j => ['senior', 'staff', 'principal'].includes(j.seniority ?? ''))
      }

      if (page === 1) {
        setAllJobs(jobs)
      } else {
        setAllJobs(prev => [...prev, ...jobs])
      }
      setHasMore(res.has_more)
      setDataSource({ source: res.data_source, label: res.label })
      return res
    },
    placeholderData: (prev: any) => prev,
  })

  const resetFilters = useCallback(() => {
    setSearch(''); setRole(''); setLevel(''); setSort('newest')
    setWorkType(''); setVisaOnly(false); setEntryLevel(false)
    setPostedWithin(''); setCity(''); setPage(1); setAllJobs([])
  }, [])

  const applyFilter = useCallback((updater: () => void) => {
    updater()
    setPage(1)
    setAllJobs([])
  }, [])

  const hasFilters = !!(search || role || level || workType || visaOnly || entryLevel || postedWithin || city)
  const totalDisplay = allJobs.length > 0
    ? `${allJobs.length}+ roles`
    : isLoading ? 'Loading...' : '0 roles'

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-secondary to-background">
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
              <p className="text-foreground-secondary text-sm">{totalDisplay} from 75+ top companies</p>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              {dataSource && <DataSourceBadge {...dataSource} />}
              <Link href="/trends" className="text-xs text-primary-400 hover:underline flex items-center gap-1">
                <TrendingUp className="w-3 h-3" />Market trends
              </Link>
            </div>
          </div>
        </motion.div>

        {/* Freshness banner */}
        <FreshnessBanner stats={jmiStats} />

        {/* Filters */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card glass className="mb-6 p-4">
            <div className="flex flex-col gap-3">
              {/* Quick chips */}
              <div className="flex flex-wrap gap-2">
                {([
                  { id: 'hot', label: '🔥 Last 4h', active: postedWithin === '4h', action: () => setPostedWithin(v => v === '4h' ? '' : '4h') },
                  { id: 'entry', label: '🎓 Entry-Level', active: entryLevel, action: () => setEntryLevel(v => !v) },
                  { id: 'remote', label: '🌍 Remote', active: workType === 'remote', action: () => setWorkType(v => v === 'remote' ? '' : 'remote') },
                  { id: 'visa', label: '✈️ Visa OK', active: visaOnly, action: () => setVisaOnly(v => !v) },
                  { id: 'salary', label: '$$ Top Pay', active: sort === 'salary_desc', action: () => setSort(v => v === 'salary_desc' ? 'newest' : 'salary_desc') },
                ] as const).map(chip => (
                  <button
                    key={chip.id}
                    onClick={() => applyFilter(chip.action)}
                    className={`px-3 py-1.5 rounded-full border text-xs font-medium transition-colors ${
                      chip.active
                        ? 'bg-primary-500/20 border-primary-500/50 text-primary-300'
                        : 'bg-background border-foreground-muted/20 text-foreground-secondary hover:border-primary-500/30 hover:text-primary-300'
                    }`}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>

              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
                <input
                  type="text"
                  placeholder="Search by company, role, or skill..."
                  value={search}
                  onChange={e => applyFilter(() => setSearch(e.target.value))}
                  className="w-full pl-9 pr-9 py-2.5 bg-background border border-foreground-muted/20 rounded-lg text-sm focus:outline-none focus:border-primary-500/50 text-foreground placeholder:text-foreground-muted"
                />
                {search && (
                  <button onClick={() => applyFilter(() => setSearch(''))} className="absolute right-3 top-1/2 -translate-y-1/2">
                    <X className="w-4 h-4 text-foreground-muted hover:text-foreground" />
                  </button>
                )}
              </div>

              {/* Filter dropdowns row 1 */}
              <div className="flex flex-wrap gap-2 items-center">
                <FilterSelect value={role} onChange={v => applyFilter(() => setRole(v))} options={ROLE_OPTIONS} />
                <FilterSelect value={level} onChange={v => applyFilter(() => setLevel(v))} options={LEVEL_OPTIONS} />
                <FilterSelect value={workType} onChange={v => applyFilter(() => setWorkType(v))} options={WORK_TYPE_OPTIONS} />
                <FilterSelect value={sort} onChange={v => applyFilter(() => setSort(v))} options={SORT_OPTIONS} />
                <FilterSelect value={postedWithin} onChange={v => applyFilter(() => setPostedWithin(v))} options={POSTED_WITHIN_OPTIONS} />

                {/* City search */}
                <div className="relative">
                  <input
                    type="text"
                    placeholder="City..."
                    value={city}
                    onChange={e => applyFilter(() => setCity(e.target.value))}
                    className="pl-3 pr-7 py-2 rounded-lg border border-foreground-muted/20 text-sm focus:outline-none focus:border-primary-500/50 transition-colors min-w-[100px]"
                    style={{ backgroundColor: '#1e293b', color: '#f8fafc' }}
                  />
                  {city && (
                    <button onClick={() => applyFilter(() => setCity(''))} className="absolute right-2 top-1/2 -translate-y-1/2">
                      <X className="w-3 h-3 text-foreground-muted" />
                    </button>
                  )}
                </div>

                {hasFilters && (
                  <button onClick={resetFilters} className="flex items-center gap-1 px-2 py-2 text-sm text-foreground-muted hover:text-foreground transition-colors">
                    <X className="w-3.5 h-3.5" />Reset
                  </button>
                )}
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Job list */}
        <div className="space-y-3">
          {isLoading && page === 1 ? (
            Array.from({ length: 8 }).map((_, i) => <JobCardSkeleton key={i} />)
          ) : isError ? (
            <div className="text-center py-16">
              <Briefcase className="w-10 h-10 text-foreground-muted mx-auto mb-3" />
              <p className="text-foreground-secondary font-medium">Backend is starting up</p>
              <p className="text-foreground-muted text-sm mt-1">The server wakes on first request — wait ~30s and try again.</p>
              <button onClick={() => { setAllJobs([]); setPage(1) }} className="mt-4 text-primary-400 text-sm hover:underline">Retry</button>
            </div>
          ) : allJobs.length === 0 ? (
            <div className="text-center py-16">
              <Briefcase className="w-10 h-10 text-foreground-muted mx-auto mb-3" />
              {postedWithin === '4h' ? (
                <>
                  <p className="text-foreground-secondary font-medium">No new jobs in the last 4 hours.</p>
                  <p className="text-foreground-muted text-sm mt-1">The scraper runs every 4h — try "Last 24h" or "Last 7 days".</p>
                  <button onClick={() => { applyFilter(() => setPostedWithin('24h')) }} className="mt-3 text-primary-400 text-sm hover:underline">Show last 24h</button>
                </>
              ) : postedWithin === '24h' ? (
                <>
                  <p className="text-foreground-secondary font-medium">No new jobs scraped today yet.</p>
                  <p className="text-foreground-muted text-sm mt-1">The scraper runs every 4 hours — check back soon.</p>
                  <button onClick={resetFilters} className="mt-3 text-primary-400 text-sm hover:underline">Reset filters</button>
                </>
              ) : (
                <>
                  <p className="text-foreground-secondary">No jobs match your filters.</p>
                  <button onClick={resetFilters} className="mt-3 text-primary-400 text-sm hover:underline">Reset filters</button>
                </>
              )}
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
                  <Button onClick={() => setPage(p => p + 1)} variant="outline" disabled={isFetching}>
                    {isFetching ? 'Loading...' : 'Load More Jobs'}
                  </Button>
                </div>
              )}

              {isFetching && page > 1 &&
                Array.from({ length: 3 }).map((_, i) => <JobCardSkeleton key={`sk-${i}`} />)
              }
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
            {' '}&middot; MS CS at CSULB &middot; Powered by FastAPI, Next.js, and Groq LLM
          </p>
        </footer>
      </div>
    </div>
  )
}
