'use client'

import { useState } from 'react'
import { MapPin, DollarSign, ExternalLink, Wifi, Globe } from 'lucide-react'
import { JobPosting } from '@/types/api'

const ROLE_COLORS: Record<string, string> = {
  ml_engineer: 'bg-blue-500/15 text-blue-300 border-blue-500/25',
  data_scientist: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
  mlops: 'bg-orange-500/15 text-orange-300 border-orange-500/25',
  analytics: 'bg-purple-500/15 text-purple-300 border-purple-500/25',
  applied_scientist: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/25',
  research: 'bg-pink-500/15 text-pink-300 border-pink-500/25',
}

const SENIORITY_COLORS: Record<string, string> = {
  intern: 'bg-yellow-500/15 text-yellow-300',
  junior: 'bg-lime-500/15 text-lime-300',
  mid: 'bg-sky-500/15 text-sky-300',
  senior: 'bg-violet-500/15 text-violet-300',
  staff: 'bg-rose-500/15 text-rose-300',
  principal: 'bg-amber-500/15 text-amber-300',
}

const ROLE_LABELS: Record<string, string> = {
  ml_engineer: 'ML Engineer', data_scientist: 'Data Scientist',
  mlops: 'MLOps', analytics: 'Analytics',
  applied_scientist: 'Applied Scientist', research: 'Research',
}

function CompanyLogo({ company, domain }: { company: string; domain?: string }) {
  const [err, setErr] = useState(false)
  const d = domain || `${company.toLowerCase().replace(/\s+/g, '')}.com`
  if (err) {
    return (
      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-600/30 to-accent-600/30 flex items-center justify-center text-sm font-bold text-primary-300 flex-shrink-0">
        {company.charAt(0)}
      </div>
    )
  }
  return (
    <img
      src={`https://logo.clearbit.com/${d}`}
      alt={company}
      onError={() => setErr(true)}
      className="w-10 h-10 rounded-lg object-contain bg-white p-1 flex-shrink-0"
    />
  )
}

export function JobCardSkeleton() {
  return (
    <div className="rounded-xl p-5 bg-background-secondary border border-foreground-muted/10 animate-pulse">
      <div className="flex gap-4">
        <div className="w-10 h-10 rounded-lg bg-foreground-muted/20 flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-foreground-muted/20 rounded w-1/3" />
          <div className="h-5 bg-foreground-muted/20 rounded w-2/3" />
          <div className="h-3 bg-foreground-muted/20 rounded w-1/2" />
        </div>
        <div className="w-20 h-8 bg-foreground-muted/20 rounded-lg flex-shrink-0" />
      </div>
    </div>
  )
}

interface JobCardProps {
  job: JobPosting
  matchScore?: number
}

export function JobCard({ job, matchScore }: JobCardProps) {
  const roleColor = ROLE_COLORS[job.role_category ?? ''] ?? 'bg-foreground-muted/15 text-foreground-secondary'
  const seniorityColor = SENIORITY_COLORS[job.seniority ?? ''] ?? 'bg-foreground-muted/15 text-foreground-secondary'

  const hasSalary = job.salary_min && job.salary_max
  const visaIcon = job.visa_sponsorship === true
    ? <span className="text-green-400 text-xs font-medium">Visa</span>
    : job.visa_sponsorship === false
    ? <span className="text-red-400 text-xs font-medium line-through opacity-60">Visa</span>
    : null

  const displayScore = matchScore ?? job.match_score
  const scoreColor = displayScore == null ? '' : displayScore >= 80 ? 'text-green-400' : displayScore >= 60 ? 'text-yellow-400' : 'text-foreground-muted'

  const visibleSkills = (job.skills_required || []).slice(0, 6)
  const extraSkills = (job.skills_required || []).length - 6

  return (
    <div className="group rounded-xl p-4 bg-background-secondary border border-foreground-muted/10 hover:border-primary-500/30 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
      <div className="flex items-start gap-4">
        <CompanyLogo company={job.company} />

        <div className="flex-1 min-w-0">
          {/* badges row */}
          <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
            {job.role_category && (
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${roleColor}`}>
                {ROLE_LABELS[job.role_category] ?? job.role_category}
              </span>
            )}
            {job.seniority && (
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${seniorityColor}`}>
                {job.seniority}
              </span>
            )}
            {job.remote && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-teal-500/15 text-teal-300 flex items-center gap-1">
                <Wifi className="w-2.5 h-2.5" />Remote
              </span>
            )}
            {visaIcon}
          </div>

          {/* title */}
          <h3 className="font-semibold text-base leading-tight truncate group-hover:text-primary-300 transition-colors">
            {job.title}
          </h3>

          {/* company + location */}
          <p className="text-foreground-secondary text-sm mt-0.5">
            {job.company}
            {job.location && (
              <span className="text-foreground-muted">
                {' '}&middot;{' '}
                <MapPin className="w-3 h-3 inline -mt-0.5" />
                {' '}{job.location}
              </span>
            )}
          </p>

          {/* salary */}
          {hasSalary ? (
            <p className="text-green-400 text-sm font-medium mt-1">
              <DollarSign className="w-3.5 h-3.5 inline -mt-0.5" />
              {job.salary_min!.toLocaleString()} – {job.salary_max!.toLocaleString()}
            </p>
          ) : (
            <p className="text-foreground-muted text-xs mt-1">Salary not disclosed</p>
          )}

          {/* required skills */}
          {visibleSkills.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {visibleSkills.map((s, i) => (
                <span key={i} className="px-1.5 py-0.5 rounded bg-primary-500/10 border border-primary-500/20 text-primary-300 text-xs">
                  {s}
                </span>
              ))}
              {extraSkills > 0 && (
                <span className="text-foreground-muted text-xs self-center">+{extraSkills} more</span>
              )}
            </div>
          )}

          {/* nice-to-have skills */}
          {(job.skills_nice_to_have || []).length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {(job.skills_nice_to_have || []).slice(0, 3).map((s, i) => (
                <span key={i} className="px-1.5 py-0.5 rounded bg-foreground-muted/10 text-foreground-muted text-xs">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* right column */}
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          {displayScore != null && (
            <div className="text-center">
              <div className={`text-xl font-bold ${scoreColor}`}>{displayScore}%</div>
              <div className="text-xs text-foreground-muted">match</div>
            </div>
          )}
          <a
            href={job.source_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-500/15 border border-primary-500/25 text-primary-400 text-sm font-medium hover:bg-primary-500/25 transition-colors whitespace-nowrap"
          >
            Apply <ExternalLink className="w-3 h-3" />
          </a>
          {job.posted_at && (
            <span className="text-foreground-muted text-xs">
              {Math.max(1, Math.round((Date.now() - new Date(job.posted_at).getTime()) / 86400000))}d ago
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
