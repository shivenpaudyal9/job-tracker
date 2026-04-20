'use client'

import { motion } from 'framer-motion'
import { Code2, Globe, Zap, Clock } from 'lucide-react'
import { Card } from '@/components/ui/Card'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://job-tracker-5cjf.onrender.com'

interface Endpoint {
  method: 'GET' | 'POST'
  path: string
  description: string
  params?: { name: string; type: string; desc: string }[]
  body?: string
  response: string
  curl: string
}

const ENDPOINTS: Endpoint[] = [
  {
    method: 'GET',
    path: '/api/stats',
    description: 'Public meta stats about the JMI database: total jobs scraped, this week\'s count, companies tracked, last scrape timestamp.',
    response: JSON.stringify({ total_jobs_scraped: 4821, jobs_this_week: 312, companies_tracked: 87, last_scrape_at: '2026-04-20T06:01:23Z' }, null, 2),
    curl: `curl ${API_BASE}/api/stats`,
  },
  {
    method: 'GET',
    path: '/api/trends/weekly',
    description: 'Latest weekly market intelligence report including top companies, skills, salary ranges, and an AI-generated narrative.',
    response: JSON.stringify({ week_start: '2026-04-14', total_jobs: 312, report: { top_companies: [{ company: 'OpenAI', count: 12 }], top_skills: [{ skill: 'python', count: 198 }], narrative: '…' } }, null, 2),
    curl: `curl ${API_BASE}/api/trends/weekly`,
  },
  {
    method: 'GET',
    path: '/api/jobs/recent',
    description: 'Recent ML/DS job postings. Optionally filter by role category.',
    params: [
      { name: 'role', type: 'string', desc: 'ml_engineer | data_scientist | mlops | analytics | applied_scientist | research' },
      { name: 'limit', type: 'integer', desc: 'Max results (1–200, default 50)' },
    ],
    response: JSON.stringify({ total: 50, data: [{ id: 'uuid', company: 'Anthropic', title: 'ML Engineer', role_category: 'ml_engineer', skills_required: ['Python', 'PyTorch'], source_url: 'https://…' }] }, null, 2),
    curl: `curl "${API_BASE}/api/jobs/recent?role=ml_engineer&limit=20"`,
  },
  {
    method: 'GET',
    path: '/api/skills/trending',
    description: 'Trending skills with week-over-week percentage change over a rolling window.',
    params: [
      { name: 'window', type: 'integer', desc: 'Days to look back (7–90, default 30)' },
    ],
    response: JSON.stringify({ window_days: 30, skills: [{ skill: 'python', mentions: 421, pct_change: 12.3 }, { skill: 'pytorch', mentions: 310, pct_change: -4.1 }] }, null, 2),
    curl: `curl "${API_BASE}/api/skills/trending?window=30"`,
  },
  {
    method: 'POST',
    path: '/api/match',
    description: 'Find top 20 job postings semantically matching a resume. Uses all-MiniLM-L6-v2 embeddings + cosine similarity. Your resume text is not stored in full.',
    body: JSON.stringify({ resume_text: 'Experienced ML engineer with 4 years in Python, PyTorch, and distributed training on AWS...' }, null, 2),
    response: JSON.stringify({ matches: [{ id: 'uuid', company: 'Databricks', title: 'Senior ML Engineer', match_score: 91.4, skills_required: ['Python', 'Spark', 'MLflow'] }], note: 'Your resume is embedded locally and not stored in full.' }, null, 2),
    curl: `curl -X POST ${API_BASE}/api/match \\
  -H "Content-Type: application/json" \\
  -d '{"resume_text": "Experienced ML engineer..."}'`,
  },
]

const METHOD_COLORS: Record<string, string> = {
  GET: 'text-green-400 bg-green-500/10 border-green-500/20',
  POST: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
}

function EndpointCard({ ep, index }: { ep: Endpoint; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07 }}
    >
      <Card glass className="mb-6">
        {/* Method + path */}
        <div className="flex items-center gap-3 mb-3">
          <span className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold border ${METHOD_COLORS[ep.method]}`}>
            {ep.method}
          </span>
          <code className="text-sm font-mono text-primary-300">{ep.path}</code>
        </div>

        <p className="text-foreground-secondary text-sm mb-4">{ep.description}</p>

        {/* Params */}
        {ep.params && (
          <div className="mb-4">
            <div className="text-xs font-semibold text-foreground-muted uppercase tracking-wider mb-2">Query Parameters</div>
            <div className="space-y-1.5">
              {ep.params.map((p, i) => (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <code className="text-accent-300 font-mono text-xs min-w-[100px]">{p.name}</code>
                  <span className="text-foreground-muted text-xs min-w-[60px]">{p.type}</span>
                  <span className="text-foreground-secondary text-xs">{p.desc}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Body */}
        {ep.body && (
          <div className="mb-4">
            <div className="text-xs font-semibold text-foreground-muted uppercase tracking-wider mb-2">Request Body</div>
            <pre className="bg-background rounded-lg p-3 text-xs text-foreground-secondary overflow-x-auto border border-foreground-muted/10">
              {ep.body}
            </pre>
          </div>
        )}

        {/* curl */}
        <div className="mb-4">
          <div className="text-xs font-semibold text-foreground-muted uppercase tracking-wider mb-2">Example</div>
          <pre className="bg-background rounded-lg p-3 text-xs text-green-400 overflow-x-auto border border-foreground-muted/10">
            {ep.curl}
          </pre>
        </div>

        {/* Response */}
        <div>
          <div className="text-xs font-semibold text-foreground-muted uppercase tracking-wider mb-2">Response</div>
          <pre className="bg-background rounded-lg p-3 text-xs text-foreground-secondary overflow-x-auto border border-foreground-muted/10 max-h-48">
            {ep.response}
          </pre>
        </div>
      </Card>
    </motion.div>
  )
}

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-secondary to-background">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary-600/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent-600/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '-3s' }} />
      </div>

      <div className="relative z-10 container mx-auto px-6 py-10 max-w-4xl">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <Code2 className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold">Public API</h1>
          </div>
          <p className="text-foreground-secondary mb-6">
            Use the JMI (Job Market Intelligence) API to power your own tooling. All endpoints are public and require no authentication.
          </p>

          {/* Meta badges */}
          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
              <Globe className="w-3.5 h-3.5" />
              No auth required
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-sm">
              <Clock className="w-3.5 h-3.5" />
              100 requests / hour / IP
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm">
              <Zap className="w-3.5 h-3.5" />
              Base: <code className="ml-1 font-mono text-xs">{API_BASE}</code>
            </div>
          </div>
        </motion.div>

        {/* Endpoints */}
        {ENDPOINTS.map((ep, i) => (
          <EndpointCard key={ep.path} ep={ep} index={i} />
        ))}

        {/* Footer */}
        <div className="mt-8 text-center text-foreground-muted text-sm border-t border-foreground-muted/10 pt-8">
          Built by <span className="text-foreground-secondary font-medium">Shiven Paudyal</span>
          {' · '}
          <a href="https://github.com/shivenpaudyal9/job-tracker" target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline">
            GitHub
          </a>
        </div>
      </div>
    </div>
  )
}
