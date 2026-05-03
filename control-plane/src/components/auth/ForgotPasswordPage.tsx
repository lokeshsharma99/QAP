'use client'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Loader2, Zap, CheckCircle } from 'lucide-react'
import { toast } from 'sonner'

export default function ForgotPasswordPage() {
  const { selectedEndpoint } = useStore()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedEndpoint) { toast.error('No API endpoint configured.'); return }
    setLoading(true)
    try {
      await fetch(APIRoutes.AuthForgotPassword(selectedEndpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      // Always show success to prevent email enumeration
      setDone(true)
    } catch {
      setDone(true) // Still hide error to prevent enumeration
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, ease: 'easeOut' }}
        className="w-full max-w-md space-y-8"
      >
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 mb-2">
            <Zap className="w-6 h-6 text-primary" />
          </div>
          <h1 className="text-2xl font-bold">Reset Password</h1>
          <p className="text-sm text-muted-foreground">
            Enter your email and we&apos;ll send a reset link if an account exists.
          </p>
        </div>

        {done ? (
          <div className="bg-card border border-border rounded-2xl p-8 flex flex-col items-center gap-4">
            <CheckCircle className="w-10 h-10 text-positive" />
            <p className="text-sm text-center text-muted-foreground">
              If <strong>{email}</strong> is registered, a password reset link has been sent.
              <br />Check your inbox (and spam folder).
            </p>
            <a href="/sign-in" className="text-sm text-primary hover:underline">Back to Sign In</a>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="bg-card border border-border rounded-2xl p-8 space-y-4 shadow-sm">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Email</label>
              <input
                type="email" required autoFocus
                value={email} onChange={e => setEmail(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                placeholder="you@company.com"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Send Reset Link
            </Button>
          </form>
        )}

        <p className="text-center text-xs text-muted-foreground">
          Remembered it?{' '}
          <a href="/sign-in" className="text-primary hover:underline">Sign in</a>
        </p>
      </motion.div>
    </div>
  )
}
