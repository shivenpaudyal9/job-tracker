'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Search, ExternalLink, MapPin, DollarSign, Briefcase, Shield, Upload } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { api } from '@/lib/api'
import { JobPosting } from '@/types/api'
import { toast } from 'sonner'

const ROLE_COLORS: Record<string, string> = {
  ml_engineer: 'primary',
  data_scientist: 'success',
  mlops: 'warning',
  analytics: 'default',
  applied_scientist: 'primary',
  research: 'default',
}

function MatchCard({ job, index }: { job: JobPosting; index: number }) {
  const score = job.match_score
  const scoreColor = score == null ? '' : score >= 80 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-foreground-secondary'

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
    >
      <Card glass className="hover:border-primary-500/30 border border-transparent transition-all duration-200">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              {job.role_category && (
                <Badge variant={(ROLE_COLORS[job.role_category] ?? 'default') as any}>
                  {job.role_category.replace('_', ' ')}
                </Badge>
              )}
              {job.remote && (
                <Badge variant="success">Remote</Badge>
              )}
              {job.seniority && (
                <span className="text-xs text-foreground-muted capitalize">{job.seniority}</span>
              )}
            </div>

            <h3 className="font-semibold text-base truncate">{job.title}</h3>
            <p className="text-foreground-secondary text-sm">{job.company}</p>

            {job.location && (
              <div className="flex items-center gap-1 text-foreground-muted text-xs mt-1">
                <MapPin className="w-3 h-3" />
                {job.location}
              </div>
            )}

            {job.salary_min && job.salary_max && (
              <div className="flex items-center gap-1 text-foreground-muted text-xs mt-1">
                <DollarSign className="w-3 h-3" />
                ${job.salary_min.toLocaleString()} – ${job.salary_max.toLocaleString()}
              </div>
            )}

            {job.skills_required?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {job.skills_required.slice(0, 6).map((s, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-full bg-primary-500/10 text-primary-300 text-xs border border-primary-500/20">
                    {s}
                  </span>
                ))}
                {job.skills_required.length > 6 && (
                  <span className="text-xs text-foreground-muted self-center">+{job.skills_required.length - 6} more</span>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col items-end gap-3 flex-shrink-0">
            {score != null && (
              <div className="text-center">
                <div className={`text-2xl font-bold ${scoreColor}`}>{score}%</div>
                <div className="text-xs text-foreground-muted">match</div>
              </div>
            )}
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary-500/10 border border-primary-500/20 text-primary-400 text-sm hover:bg-primary-500/20 transition-colors"
            >
              Apply <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}

async function extractTextFromFile(file: File): Promise<string> {
  if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = e => resolve(e.target?.result as string)
      reader.onerror = () => reject(new Error('Failed to read file'))
      reader.readAsText(file)
    })
  }
  const { api } = await import('@/lib/api')
  const result = await api.extractResume(file)
  return result.text
}

export default function MatchPage() {
  const [resumeText, setResumeText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isParsing, setIsParsing] = useState(false)
  const [matches, setMatches] = useState<JobPosting[] | null>(null)
  const [note, setNote] = useState('')
  const [matchMethod, setMatchMethod] = useState<'semantic' | 'keyword' | null>(null)
  const [backendError, setBackendError] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!isLoading) { setElapsed(0); return }
    const t = setInterval(() => setElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [isLoading])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setIsParsing(true)
    try {
      const text = await extractTextFromFile(file)
      setResumeText(text)
      toast.success(`Loaded ${file.name}`)
    } catch (err: any) {
      toast.error(err.message || 'Failed to read file')
    } finally {
      setIsParsing(false)
      e.target.value = ''
    }
  }

  const handleSubmit = async () => {
    if (resumeText.trim().length < 50) {
      toast.error('Please paste at least 50 characters of your resume')
      return
    }
    abortRef.current = new AbortController()
    const timeout = setTimeout(() => abortRef.current?.abort(), 120_000)
    setIsLoading(true)
    setMatches(null)
    setMatchMethod(null)
    setBackendError(false)
    try {
      const result = await api.matchResume(resumeText, abortRef.current.signal)
      setMatches(result.matches)
      setNote(result.note ?? '')
      setMatchMethod((result as any).method ?? null)
      if (result.matches.length === 0) {
        toast.info('No matches found yet — the job database may still be building up.')
      }
    } catch (e: any) {
      setBackendError(true)
      const msg = e.name === 'AbortError'
        ? 'Timed out after 2 min — the model is loading on first run. Try again in 30s.'
        : 'Backend is starting up — wait ~30s and try again'
      toast.error(msg)
    } finally {
      clearTimeout(timeout)
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-secondary to-background">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary-600/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent-600/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '-3s' }} />
      </div>

      <div className="relative z-10 container mx-auto px-6 py-10 max-w-4xl">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold">Resume Match</h1>
          </div>
          <p className="text-foreground-secondary">
            Paste your resume and find the top ML/DS jobs that match your background using semantic similarity.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card glass className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium">Your Resume</label>
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt,.docx"
                  className="hidden"
                  onChange={handleFileUpload}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isParsing}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-foreground-muted/20 text-xs text-foreground-secondary hover:border-primary-500/40 hover:text-primary-400 transition-colors disabled:opacity-50"
                >
                  <Upload className="w-3.5 h-3.5" />
                  {isParsing ? 'Reading…' : 'Upload PDF / DOCX / TXT'}
                </button>
              </div>
            </div>
            <textarea
              className="w-full h-48 bg-background border border-foreground-muted/20 rounded-lg p-3 text-sm text-foreground resize-y focus:outline-none focus:border-primary-500/50 placeholder:text-foreground-muted"
              placeholder="Paste your resume text here, or upload a file above..."
              value={resumeText}
              onChange={e => setResumeText(e.target.value)}
            />
            <div className="flex items-center justify-between mt-3">
              <div className="flex items-center gap-1.5 text-foreground-muted text-xs">
                <Shield className="w-3 h-3" />
                {note || 'Your resume is not stored in full'}
              </div>
              <div className="flex items-center gap-2">
                {backendError && (
                  <span className="text-xs text-yellow-400">Backend waking up — retry in ~30s</span>
                )}
                <Button
                  onClick={handleSubmit}
                  disabled={isLoading || isParsing || resumeText.trim().length < 50}
                >
                  {isLoading ? (
                    <>Finding matches…</>
                  ) : (
                    <><Search className="w-4 h-4 mr-2" />Find my best-fit roles</>
                  )}
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>

        <AnimatePresence>
          {matches !== null && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">
                  {matches.length > 0 ? `${matches.length} Best-Fit Roles` : 'No matches found'}
                </h2>
                <div className="flex items-center gap-2">
                  {matchMethod === 'keyword' && (
                    <span className="text-xs px-2 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-400">
                      Keyword match
                    </span>
                  )}
                  {matchMethod === 'semantic' && (
                    <span className="text-xs px-2 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-green-400">
                      Semantic match
                    </span>
                  )}
                  <span className="text-foreground-muted text-sm">Ranked by similarity</span>
                </div>
              </div>
              <div className="space-y-3">
                {matches.map((job, i) => (
                  <MatchCard key={job.id} job={job} index={i} />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {isLoading && (
          <div className="text-center py-16">
            <div className="w-12 h-12 rounded-full border-2 border-primary-500/30 border-t-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-foreground-secondary">Matching your resume against the job pool…</p>
            <p className="text-foreground-muted text-sm mt-2">{elapsed}s elapsed · usually 10–20s</p>
            {elapsed >= 15 && (
              <p className="text-yellow-400/80 text-xs mt-2">
                Embedding API is warming up — almost there.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
