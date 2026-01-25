'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Briefcase, Zap, Target, TrendingUp, Mail, CheckCircle2, ArrowRight, LogIn, Shield, X, ExternalLink, Key, Settings, UserCheck } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { api } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'

export default function LandingPage() {
  const router = useRouter()
  const { isAuthenticated, user, isLoading: authLoading } = useAuth()
  const [isConnected, setIsConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showHowItWorks, setShowHowItWorks] = useState(false)

  useEffect(() => {
    // Only check sync status if authenticated
    if (isAuthenticated) {
      api.getSyncStatus()
        .then(status => {
          setIsConnected(status.is_connected)
          setLoading(false)
        })
        .catch(() => {
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [isAuthenticated])

  const handleGetStarted = () => {
    if (!isAuthenticated) {
      router.push('/register')
    } else if (isConnected) {
      router.push('/dashboard')
    } else {
      router.push('/setup')
    }
  }

  const features = [
    {
      icon: Mail,
      title: 'Auto Email Sync',
      description: 'Automatically fetch and process job emails from your Outlook inbox',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      icon: Zap,
      title: 'Smart Extraction',
      description: 'AI-powered extraction of company, job title, status, and deadlines',
      color: 'from-purple-500 to-pink-500',
    },
    {
      icon: Target,
      title: 'Action Tracking',
      description: 'Never miss an interview, assessment, or follow-up deadline',
      color: 'from-orange-500 to-red-500',
    },
    {
      icon: TrendingUp,
      title: 'Analytics',
      description: 'Track your application success rate and optimize your job search',
      color: 'from-green-500 to-emerald-500',
    },
  ]

  const stats = [
    { label: 'Emails Processed', value: '1000+' },
    { label: 'Time Saved', value: '20hrs' },
    { label: 'Accuracy', value: '95%' },
    { label: 'Applications', value: '100+' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-secondary to-background relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary-600/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent-600/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '-3s' }} />
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-primary-600/5 to-accent-600/5 rounded-full blur-3xl" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className="container mx-auto px-6 py-6">
          <nav className="flex items-center justify-between">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-2"
            >
              <Briefcase className="w-8 h-8 text-primary-400" />
              <span className="text-2xl font-bold gradient-text">Job Tracker</span>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3"
            >
              {!authLoading && (
                isAuthenticated ? (
                  <Button onClick={() => router.push('/dashboard')}>
                    Go to Dashboard
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                ) : (
                  <>
                    <Button variant="ghost" onClick={() => router.push('/login')}>
                      <LogIn className="w-4 h-4 mr-2" />
                      Sign In
                    </Button>
                    <Button onClick={() => router.push('/register')}>
                      Get Started
                    </Button>
                  </>
                )
              )}
            </motion.div>
          </nav>
        </header>

        {/* Hero Section */}
        <section className="container mx-auto px-6 pt-20 pb-32">
          <div className="max-w-5xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-block mb-6">
                <span className="px-4 py-2 rounded-full bg-gradient-to-r from-primary-500/20 to-accent-500/20 border border-primary-500/30 text-primary-300 text-sm font-medium">
                  ✨ Automate Your Job Search
                </span>
              </div>

              <h1 className="text-6xl md:text-7xl font-bold mb-6 leading-tight">
                Track Every Job Application{' '}
                <span className="gradient-text">Automatically</span>
              </h1>

              <p className="text-xl text-foreground-secondary mb-10 max-w-3xl mx-auto leading-relaxed">
                Stop manually tracking your job applications. Connect your Outlook, and let AI automatically
                extract company names, job titles, interview dates, and deadlines from your emails.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Button size="lg" onClick={handleGetStarted}>
                  <Zap className="w-5 h-5 mr-2" />
                  {isConnected ? 'Open Dashboard' : 'Start Free'}
                </Button>
                <Button size="lg" variant="outline" onClick={() => setShowHowItWorks(true)}>
                  See How It Works
                </Button>
              </div>
            </motion.div>

            {/* Stats Cards */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6"
            >
              {stats.map((stat, index) => (
                <Card key={index} glass hover className="text-center">
                  <div className="text-3xl font-bold gradient-text">{stat.value}</div>
                  <div className="text-sm text-foreground-secondary mt-1">{stat.label}</div>
                </Card>
              ))}
            </motion.div>
          </div>
        </section>

        {/* Features Section */}
        <section className="container mx-auto px-6 py-20">
          <div className="max-w-6xl mx-auto">
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <h2 className="text-4xl font-bold mb-4">Powerful Features</h2>
              <p className="text-xl text-foreground-secondary">
                Everything you need to manage your job search in one place
              </p>
            </motion.div>

            <div className="grid md:grid-cols-2 gap-8">
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card glass hover className="h-full">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} p-2.5 mb-4`}>
                      <feature.icon className="w-full h-full text-white" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                    <p className="text-foreground-secondary">{feature.description}</p>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="container mx-auto px-6 py-20">
          <div className="max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <h2 className="text-4xl font-bold mb-4">How It Works</h2>
              <p className="text-xl text-foreground-secondary">
                Get started in 3 simple steps
              </p>
            </motion.div>

            <div className="space-y-8">
              {[
                { step: 1, title: 'Connect Outlook', description: 'One-click secure connection to your personal Outlook account using Microsoft authentication' },
                { step: 2, title: 'Auto Sync Emails', description: 'We automatically fetch and process job-related emails from your inbox' },
                { step: 3, title: 'Track Applications', description: 'View all your applications in one dashboard with deadlines, statuses, and actions' },
              ].map((item, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card glass className="flex items-start space-x-6">
                    <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-xl font-bold shadow-glow">
                      {item.step}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                      <p className="text-foreground-secondary">{item.description}</p>
                    </div>
                    <CheckCircle2 className="w-6 h-6 text-green-400 flex-shrink-0" />
                  </Card>
                </motion.div>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="mt-12 text-center"
            >
              <Button size="lg" onClick={handleGetStarted}>
                {isConnected ? 'Go to Dashboard' : 'Get Started Now'}
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </motion.div>
          </div>
        </section>

        {/* Footer */}
        <footer className="container mx-auto px-6 py-12 border-t border-foreground-muted/10">
          <div className="text-center text-foreground-muted">
            <p>© 2026 Job Tracker. Automate your job search with AI.</p>
          </div>
        </footer>
      </div>

      {/* How It Works Modal */}
      {showHowItWorks && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-background-secondary border border-foreground-muted/20 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
          >
            {/* Modal Header */}
            <div className="sticky top-0 bg-background-secondary border-b border-foreground-muted/10 px-6 py-4 flex items-center justify-between">
              <h2 className="text-2xl font-bold">How Email Access Works</h2>
              <button
                onClick={() => setShowHowItWorks(false)}
                className="p-2 hover:bg-foreground-muted/10 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-8">
              {/* Security Notice */}
              <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <Shield className="w-6 h-6 text-green-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-green-400 mb-1">100% Secure & Private</h3>
                    <p className="text-sm text-foreground-secondary">
                      We use Microsoft's official OAuth2 authentication. We never see your password,
                      only get read-only access to your emails, and you can revoke access anytime.
                    </p>
                  </div>
                </div>
              </div>

              {/* Step 1: Azure Setup */}
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center text-sm font-bold">1</div>
                  <h3 className="text-xl font-semibold">Create Azure App Registration</h3>
                </div>
                <div className="ml-11 space-y-3">
                  <p className="text-foreground-secondary">
                    First, you need to create an app in Microsoft Azure (free) to allow Job Tracker to read your emails:
                  </p>
                  <ol className="list-decimal list-inside space-y-2 text-foreground-secondary">
                    <li>Go to <a href="https://portal.azure.com" target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline inline-flex items-center gap-1">portal.azure.com <ExternalLink className="w-3 h-3" /></a></li>
                    <li>Search for <strong>"App registrations"</strong> and click it</li>
                    <li>Click <strong>"+ New registration"</strong></li>
                    <li>Name it <strong>"Job Tracker"</strong></li>
                    <li>Select <strong>"Personal Microsoft accounts only"</strong></li>
                    <li>Redirect URI: Web → <code className="bg-background px-2 py-0.5 rounded text-sm">http://localhost:8000/callback</code></li>
                    <li>Click <strong>Register</strong></li>
                  </ol>
                </div>
              </div>

              {/* Step 2: Get Credentials */}
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center text-sm font-bold">2</div>
                  <h3 className="text-xl font-semibold">Get Your Credentials</h3>
                </div>
                <div className="ml-11 space-y-3">
                  <div className="flex items-start gap-3 p-3 bg-background rounded-lg">
                    <Key className="w-5 h-5 text-primary-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium">Client ID</p>
                      <p className="text-sm text-foreground-secondary">Copy from the Overview page → "Application (client) ID"</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-background rounded-lg">
                    <Key className="w-5 h-5 text-accent-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium">Client Secret</p>
                      <p className="text-sm text-foreground-secondary">Go to "Certificates & secrets" → "+ New client secret" → Copy the Value immediately</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 3: Set Permissions */}
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center text-sm font-bold">3</div>
                  <h3 className="text-xl font-semibold">Set API Permissions</h3>
                </div>
                <div className="ml-11 space-y-3">
                  <p className="text-foreground-secondary">
                    Go to "API permissions" → "Add a permission" → "Microsoft Graph" → "Delegated permissions"
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-3 bg-background rounded-lg text-center">
                      <Mail className="w-6 h-6 mx-auto mb-2 text-blue-400" />
                      <p className="font-medium text-sm">Mail.Read</p>
                      <p className="text-xs text-foreground-muted">Read your emails</p>
                    </div>
                    <div className="p-3 bg-background rounded-lg text-center">
                      <UserCheck className="w-6 h-6 mx-auto mb-2 text-green-400" />
                      <p className="font-medium text-sm">User.Read</p>
                      <p className="text-xs text-foreground-muted">Read your profile</p>
                    </div>
                    <div className="p-3 bg-background rounded-lg text-center">
                      <Settings className="w-6 h-6 mx-auto mb-2 text-purple-400" />
                      <p className="font-medium text-sm">offline_access</p>
                      <p className="text-xs text-foreground-muted">Stay connected</p>
                    </div>
                  </div>
                  <p className="text-sm text-foreground-secondary">
                    Then go to "Authentication" → Enable <strong>"Allow public client flows"</strong> → Save
                  </p>
                </div>
              </div>

              {/* Step 4: Connect */}
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center text-sm font-bold">4</div>
                  <h3 className="text-xl font-semibold">Connect Your Account</h3>
                </div>
                <div className="ml-11 space-y-3">
                  <p className="text-foreground-secondary">
                    After setting up Azure, add your credentials to <code className="bg-background px-2 py-0.5 rounded text-sm">backend/.env</code>,
                    then come back here and click "Get Started" to connect your Outlook account.
                  </p>
                  <p className="text-foreground-secondary">
                    You'll be shown a device code to enter at Microsoft's website - this is the safest way to authenticate without ever sharing your password.
                  </p>
                </div>
              </div>

              {/* Revoke Access */}
              <div className="bg-foreground-muted/5 border border-foreground-muted/10 rounded-xl p-4">
                <h4 className="font-semibold mb-2">🔐 Want to Revoke Access?</h4>
                <p className="text-sm text-foreground-secondary">
                  You can remove Job Tracker's access anytime at:{' '}
                  <a href="https://account.microsoft.com/privacy/app-access" target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline inline-flex items-center gap-1">
                    account.microsoft.com/privacy/app-access <ExternalLink className="w-3 h-3" />
                  </a>
                </p>
              </div>

              {/* CTA */}
              <div className="flex justify-center pt-4">
                <Button size="lg" onClick={() => { setShowHowItWorks(false); handleGetStarted(); }}>
                  <Zap className="w-5 h-5 mr-2" />
                  Get Started Now
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
