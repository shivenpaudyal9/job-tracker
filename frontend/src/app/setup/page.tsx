'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { CheckCircle2, Loader2, Mail, Play, ArrowRight, ExternalLink, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { api } from '@/lib/api'
import { toast } from 'sonner'
import { ProtectedRoute } from '@/components/ProtectedRoute'

enum SetupStep {
  CONNECT = 'connect',
  SYNCING = 'syncing',
  COMPLETE = 'complete',
}

function SetupContent() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState<SetupStep>(SetupStep.CONNECT)
  const [deviceCode, setDeviceCode] = useState<string>('')
  const [verificationUri, setVerificationUri] = useState<string>('')
  const [isPolling, setIsPolling] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncStats, setSyncStats] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Check if already connected
    api.getSyncStatus()
      .then(status => {
        if (status.is_connected) {
          setCurrentStep(SetupStep.SYNCING)
        }
      })
      .catch(console.error)
  }, [])

  const startConnection = async () => {
    setIsConnecting(true)
    setError(null)

    try {
      const response = await api.startConnect()
      setDeviceCode(response.user_code)
      setVerificationUri(response.verification_uri)
      setIsPolling(true)

      // Start polling
      pollForConnection()
    } catch (err: any) {
      setError(err.message || 'Failed to start connection')
      toast.error('Failed to start connection')
    } finally {
      setIsConnecting(false)
    }
  }

  const pollForConnection = async () => {
    let attempts = 0
    const maxAttempts = 60 // 5 minutes (5 seconds * 60)

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setIsPolling(false)
        setError('Connection timeout. Please try again.')
        toast.error('Connection timeout')
        return
      }

      try {
        const response = await api.pollConnect()

        if (response.connected) {
          setIsPolling(false)
          toast.success('Successfully connected to Outlook!')
          setCurrentStep(SetupStep.SYNCING)
        } else if (response.error && response.error !== 'authorization_pending') {
          setIsPolling(false)
          setError(response.error)
          toast.error(response.error)
        } else {
          // Continue polling
          attempts++
          setTimeout(poll, 5000)
        }
      } catch (err: any) {
        setIsPolling(false)
        setError(err.message || 'Failed to check connection status')
        toast.error('Failed to check connection')
      }
    }

    poll()
  }

  const runFirstSync = async () => {
    setIsSyncing(true)
    setError(null)

    try {
      await api.runSync(30)
      toast.success('Sync started! Processing your emails...')

      // Poll for sync completion
      const checkSync = setInterval(async () => {
        try {
          const status = await api.getSyncStatus()

          if (!status.is_running && status.last_sync_counts) {
            clearInterval(checkSync)
            setSyncStats(status.last_sync_counts)
            setIsSyncing(false)
            setCurrentStep(SetupStep.COMPLETE)
            toast.success('Sync completed successfully!')
          }
        } catch (err) {
          console.error('Error checking sync status:', err)
        }
      }, 3000)

      // Timeout after 5 minutes
      setTimeout(() => {
        clearInterval(checkSync)
        if (isSyncing) {
          setIsSyncing(false)
          setCurrentStep(SetupStep.COMPLETE)
          toast.info('Sync is taking longer than expected, but continues in the background')
        }
      }, 300000)
    } catch (err: any) {
      setIsSyncing(false)
      setError(err.message || 'Failed to start sync')
      toast.error('Failed to start sync')
    }
  }

  const openVerificationLink = () => {
    if (verificationUri) {
      window.open(verificationUri, '_blank')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-secondary to-background flex items-center justify-center p-6">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary-600/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent-600/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '-3s' }} />
      </div>

      {/* Content */}
      <div className="relative z-10 w-full max-w-2xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold mb-2">
              Setup <span className="gradient-text">Job Tracker</span>
            </h1>
            <p className="text-foreground-secondary">
              Connect your Outlook and start tracking automatically
            </p>
          </div>

          {/* Progress Steps */}
          <div className="flex items-center justify-center mb-12 space-x-4">
            {[
              { step: SetupStep.CONNECT, label: 'Connect', icon: Mail },
              { step: SetupStep.SYNCING, label: 'Sync', icon: Play },
              { step: SetupStep.COMPLETE, label: 'Done', icon: CheckCircle2 },
            ].map((item, index) => (
              <div key={index} className="flex items-center">
                <div
                  className={`flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all ${
                    currentStep === item.step
                      ? 'bg-gradient-to-br from-primary-500 to-accent-500 border-transparent shadow-glow'
                      : index < Object.values(SetupStep).indexOf(currentStep)
                      ? 'bg-green-500/20 border-green-500 text-green-400'
                      : 'bg-background-secondary border-foreground-muted text-foreground-muted'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                </div>
                {index < 2 && (
                  <div
                    className={`w-16 h-0.5 transition-all ${
                      index < Object.values(SetupStep).indexOf(currentStep)
                        ? 'bg-green-500'
                        : 'bg-foreground-muted/30'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Step Content */}
          <Card glass className="p-8">
            {/* Step 1: Connect Outlook */}
            {currentStep === SetupStep.CONNECT && (
              <div className="space-y-6">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow">
                    <Mail className="w-8 h-8 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold mb-2">Connect Your Outlook</h2>
                  <p className="text-foreground-secondary">
                    Securely connect using Microsoft device code authentication
                  </p>
                </div>

                {!deviceCode && (
                  <div className="space-y-4">
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                      <p className="text-sm text-blue-300">
                        <strong>Note:</strong> We only request read access to your emails. We never store your password or have write access to your inbox.
                      </p>
                    </div>

                    <Button
                      size="lg"
                      className="w-full"
                      onClick={startConnection}
                      isLoading={isConnecting}
                    >
                      <Mail className="w-5 h-5 mr-2" />
                      Start Connection
                    </Button>
                  </div>
                )}

                {deviceCode && (
                  <div className="space-y-6">
                    <div className="bg-gradient-to-r from-primary-500/10 to-accent-500/10 border border-primary-500/30 rounded-xl p-6 text-center">
                      <p className="text-sm text-foreground-secondary mb-4">
                        1. Click the button below to open Microsoft's authentication page
                      </p>

                      <Button
                        size="lg"
                        onClick={openVerificationLink}
                        className="mb-6"
                      >
                        <ExternalLink className="w-5 h-5 mr-2" />
                        Open Microsoft Login
                      </Button>

                      <p className="text-sm text-foreground-secondary mb-2">
                        2. Enter this code when prompted:
                      </p>

                      <div className="bg-background-secondary border border-primary-500/50 rounded-lg p-4 mb-4">
                        <div className="text-4xl font-bold gradient-text tracking-widest">
                          {deviceCode}
                        </div>
                      </div>

                      <p className="text-xs text-foreground-muted">
                        Verification URL: {verificationUri}
                      </p>
                    </div>

                    {isPolling && (
                      <div className="flex items-center justify-center space-x-3 text-primary-400">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>Waiting for you to complete authentication...</span>
                      </div>
                    )}
                  </div>
                )}

                {error && (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-start space-x-3">
                    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-red-300">{error}</p>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setError(null)
                          setDeviceCode('')
                          setVerificationUri('')
                        }}
                        className="mt-2"
                      >
                        Try Again
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Sync Emails */}
            {currentStep === SetupStep.SYNCING && (
              <div className="space-y-6">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-glow">
                    <Play className="w-8 h-8 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold mb-2">Run First Sync</h2>
                  <p className="text-foreground-secondary">
                    Fetch and process your job emails from the last 30 days
                  </p>
                </div>

                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                  <p className="text-sm text-blue-300">
                    This will scan your Outlook inbox for job-related emails and automatically extract application data.
                  </p>
                </div>

                {!isSyncing ? (
                  <Button
                    size="lg"
                    className="w-full"
                    onClick={runFirstSync}
                  >
                    <Play className="w-5 h-5 mr-2" />
                    Start Sync
                  </Button>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center justify-center space-x-3 text-primary-400 py-8">
                      <Loader2 className="w-8 h-8 animate-spin" />
                      <div>
                        <p className="font-medium">Syncing your emails...</p>
                        <p className="text-sm text-foreground-muted">This may take a minute</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Complete */}
            {currentStep === SetupStep.COMPLETE && (
              <div className="space-y-6 text-center">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', duration: 0.6 }}
                >
                  <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-glow">
                    <CheckCircle2 className="w-10 h-10 text-white" />
                  </div>
                </motion.div>

                <div>
                  <h2 className="text-3xl font-bold mb-2">All Set!</h2>
                  <p className="text-foreground-secondary">
                    Your Job Tracker is ready to use
                  </p>
                </div>

                {syncStats && (
                  <div className="grid grid-cols-2 gap-4">
                    <Card className="p-4">
                      <div className="text-2xl font-bold text-primary-400">{syncStats.emails_fetched}</div>
                      <div className="text-sm text-foreground-muted">Emails Processed</div>
                    </Card>
                    <Card className="p-4">
                      <div className="text-2xl font-bold text-green-400">{syncStats.applications_created}</div>
                      <div className="text-sm text-foreground-muted">Applications Found</div>
                    </Card>
                  </div>
                )}

                <Button
                  size="lg"
                  className="w-full"
                  onClick={() => router.push('/dashboard')}
                >
                  Go to Dashboard
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </div>
            )}
          </Card>

          {/* Back to Home */}
          {currentStep === SetupStep.CONNECT && !deviceCode && (
            <div className="text-center mt-6">
              <Button
                variant="ghost"
                onClick={() => router.push('/')}
              >
                ← Back to Home
              </Button>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

export default function SetupPage() {
  return (
    <ProtectedRoute>
      <SetupContent />
    </ProtectedRoute>
  )
}
