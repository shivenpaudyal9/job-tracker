'use client'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts'
import { TrendingUp, TrendingDown, Briefcase, Building2, Brain, RefreshCw, ArrowUpRight } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { api } from '@/lib/api'

const ROLE_LABELS: Record<string, string> = {
  ml_engineer: 'ML Engineer',
  data_scientist: 'Data Scientist',
  mlops: 'MLOps',
  analytics: 'Analytics',
  applied_scientist: 'Applied Scientist',
  research: 'Research',
}

const CHART_COLORS = ['#38bdf8', '#a78bfa', '#34d399', '#fb923c', '#f472b6', '#facc15']

export default function TrendsPage() {
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['jmi-stats'],
    queryFn: () => api.getJMIStats(),
    refetchInterval: 60_000,
  })

  const { data: reportData, isLoading: reportLoading } = useQuery({
    queryKey: ['weekly-report'],
    queryFn: () => api.getWeeklyReport(),
  })

  const { data: skillsData, isLoading: skillsLoading } = useQuery({
    queryKey: ['trending-skills'],
    queryFn: () => api.getTrendingSkills(30),
  })

  const report = reportData?.report
  const isLoading = statsLoading || reportLoading || skillsLoading

  const roleChartData = report
    ? Object.entries(report.by_role_category).map(([k, v]) => ({
        name: ROLE_LABELS[k] ?? k,
        count: v,
      }))
    : []

  const topCompaniesData = report?.top_companies?.slice(0, 10) ?? []
  const topSkillsData = skillsData?.skills?.slice(0, 20) ?? []

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-secondary to-background">
      {/* Animated bg blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary-600/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent-600/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '-3s' }} />
      </div>

      <div className="relative z-10 container mx-auto px-6 py-10 max-w-7xl">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">ML Job Market Intelligence</h1>
              <p className="text-foreground-secondary text-sm mt-0.5">
                Live data from Greenhouse, Lever & LinkedIn · Updated daily
              </p>
            </div>
          </div>
          {statsData?.last_scrape_at && (
            <div className="flex items-center gap-2 text-foreground-muted text-xs mt-2">
              <RefreshCw className="w-3 h-3" />
              Last scraped {new Date(statsData.last_scrape_at).toLocaleString()}
            </div>
          )}
        </motion.div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Jobs Tracked', value: statsData?.total_jobs_scraped?.toLocaleString() ?? '—', icon: Briefcase, color: 'from-blue-500 to-cyan-500' },
            { label: 'This Week', value: statsData?.jobs_this_week?.toLocaleString() ?? '—', icon: TrendingUp, color: 'from-green-500 to-emerald-500' },
            { label: 'Companies', value: statsData?.companies_tracked?.toLocaleString() ?? '—', icon: Building2, color: 'from-purple-500 to-pink-500' },
            { label: 'Skills Tracked', value: topSkillsData.length ? String(topSkillsData.length) + '+' : '—', icon: Brain, color: 'from-orange-500 to-red-500' },
          ].map((stat, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}>
              <Card glass className="text-center">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center mx-auto mb-3`}>
                  <stat.icon className="w-5 h-5 text-white" />
                </div>
                <div className="text-3xl font-bold gradient-text">{stat.value}</div>
                <div className="text-foreground-muted text-xs mt-1">{stat.label}</div>
              </Card>
            </motion.div>
          ))}
        </div>

        {isLoading && (
          <div className="text-center py-20 text-foreground-muted">Loading market data…</div>
        )}

        {report && (
          <>
            {/* Narrative */}
            {report.narrative && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
                <Card glass className="mb-8">
                  <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <Brain className="w-5 h-5 text-primary-400" />
                    AI Market Summary
                    <span className="text-xs text-foreground-muted font-normal ml-2">Week of {report.week_start}</span>
                  </h2>
                  <div className="space-y-3 text-foreground-secondary leading-relaxed text-sm">
                    {report.narrative.split('\n\n').filter(Boolean).map((p, i) => (
                      <p key={i}>{p}</p>
                    ))}
                  </div>
                </Card>
              </motion.div>
            )}

            <div className="grid lg:grid-cols-2 gap-8 mb-8">
              {/* Top Companies */}
              <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}>
                <Card glass>
                  <h2 className="text-lg font-semibold mb-4">Top Hiring Companies</h2>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={topCompaniesData} layout="vertical" margin={{ left: 16, right: 16 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} />
                      <YAxis type="category" dataKey="company" width={90} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
                        labelStyle={{ color: '#e2e8f0' }}
                      />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                        {topCompaniesData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </motion.div>

              {/* Role breakdown */}
              <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}>
                <Card glass>
                  <h2 className="text-lg font-semibold mb-4">Jobs by Role Category</h2>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={roleChartData} margin={{ left: 8, right: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} angle={-20} textAnchor="end" />
                      <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
                        labelStyle={{ color: '#e2e8f0' }}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {roleChartData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </motion.div>
            </div>

            {/* Skills table */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
              <Card glass className="mb-8">
                <h2 className="text-lg font-semibold mb-4">Most In-Demand Skills (Last 30 Days)</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-foreground-muted/10 text-foreground-muted text-xs uppercase">
                        <th className="text-left py-2 px-3 font-medium">Skill</th>
                        <th className="text-right py-2 px-3 font-medium">Mentions</th>
                        <th className="text-right py-2 px-3 font-medium">Trend</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topSkillsData.map((s, i) => (
                        <tr key={i} className="border-b border-foreground-muted/5 hover:bg-foreground-muted/5">
                          <td className="py-2 px-3 font-medium">{s.skill}</td>
                          <td className="py-2 px-3 text-right text-foreground-secondary">{s.mentions}</td>
                          <td className="py-2 px-3 text-right">
                            {s.pct_change >= 0 ? (
                              <span className="text-green-400 flex items-center justify-end gap-1">
                                <TrendingUp className="w-3 h-3" />+{s.pct_change}%
                              </span>
                            ) : (
                              <span className="text-red-400 flex items-center justify-end gap-1">
                                <TrendingDown className="w-3 h-3" />{s.pct_change}%
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </motion.div>

            {/* Remote vs onsite + visa */}
            <div className="grid md:grid-cols-2 gap-6">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
                <Card glass>
                  <h2 className="text-lg font-semibold mb-4">Remote vs Onsite</h2>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Remote</span>
                        <span className="text-primary-400">{report.remote_count} jobs</span>
                      </div>
                      <div className="h-2 bg-foreground-muted/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                          style={{ width: `${Math.round(report.remote_count / Math.max(report.remote_count + report.onsite_count, 1) * 100)}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Onsite</span>
                        <span className="text-foreground-secondary">{report.onsite_count} jobs</span>
                      </div>
                      <div className="h-2 bg-foreground-muted/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-foreground-muted/30 rounded-full"
                          style={{ width: `${Math.round(report.onsite_count / Math.max(report.remote_count + report.onsite_count, 1) * 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>

              {report.visa_companies?.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.55 }}>
                  <Card glass>
                    <h2 className="text-lg font-semibold mb-3">Visa-Sponsoring Companies</h2>
                    <div className="flex flex-wrap gap-2">
                      {report.visa_companies.slice(0, 15).map((c, i) => (
                        <span key={i} className="px-2 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-xs">
                          {c}
                        </span>
                      ))}
                    </div>
                  </Card>
                </motion.div>
              )}
            </div>
          </>
        )}

        {!isLoading && !report && (
          <div className="text-center py-20">
            <Brain className="w-12 h-12 text-foreground-muted mx-auto mb-4" />
            <p className="text-foreground-secondary">No report yet. The agent runs every Monday at 8am UTC.</p>
            <p className="text-foreground-muted text-sm mt-2">Daily scraping is active — check back after the first Monday run.</p>
          </div>
        )}

        {/* CTA */}
        <div className="mt-12 text-center">
          <a href="/match" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-primary-500 to-accent-500 text-white font-medium hover:opacity-90 transition-opacity">
            <Brain className="w-4 h-4" />
            Find jobs that match my resume
            <ArrowUpRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    </div>
  )
}
