'use client'
import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Loader2, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react'
import QapLogo from '@/components/auth/QapLogo'
import { toast } from 'sonner'

export default function ResetPasswordPage() {
  const router = useRouter()
  const params = useSearchParams()
  const { selectedEndpoint } = useStore()
  const [token] = useState(params.get('token') || '')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [tokenError, setTokenError] = useState(!token)

  useEffect(() => {
    if (!token) setTokenError(true)
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { toast.error('Passwords do not match.'); return }
    if (password.length < 8) { toast.error('Password must be at least 8 characters.'); return }
    if (!selectedEndpoint) { toast.error('No API endpoint configured.'); return }
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.AuthResetPassword(selectedEndpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Reset failed.' }))
        throw new Error(err.detail || 'Password reset failed.')
      }
      setDone(true)
      toast.success('Password updated! Please sign in.')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Reset failed.'
      if (msg.toLowerCase().includes('expired') || msg.toLowerCase().includes('not found')) {
        setTokenError(true)
      }
      toast.error(msg)
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
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center mb-1">
            <QapLogo size={56} />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Set New Password</h1>
          </div>
        </div>

        {tokenError && (
          <div className="flex items-center gap-3 bg-destructive/10 border border-destructive/20 rounded-xl p-4 text-destructive text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>
              This reset link is invalid or has expired.{' '}
              <a href="/forgot-password" className="underline font-medium">Request a new one.</a>
            </span>
          </div>
        )}

        {done && (
          <div className="flex flex-col items-center gap-4 bg-card border border-border rounded-2xl p-8">
            <CheckCircle className="w-10 h-10 text-positive" />
            <p className="text-sm text-muted-foreground text-center">Password updated. All existing sessions have been signed out.</p>
            <Button onClick={() => router.replace('/sign-in')} className="w-full">Sign In</Button>
          </div>
        )}

        {!tokenError && !done && (
          <form onSubmit={handleSubmit} className="bg-card border border-border rounded-2xl p-8 space-y-4 shadow-sm">
            {(['password', 'confirm'] as const).map(k => (
              <div key={k} className="space-y-1.5">
                <label className="text-sm font-medium">{k === 'password' ? 'New Password' : 'Confirm Password'}</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'} required minLength={8} autoFocus={k === 'password'}
                    value={k === 'password' ? password : confirm}
                    onChange={e => k === 'password' ? setPassword(e.target.value) : setConfirm(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2.5 pr-10 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                    placeholder="••••••••"
                  />
                  {k === 'password' && (
                    <button type="button" onClick={() => setShowPassword(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  )}
                </div>
              </div>
            ))}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Update Password
            </Button>
          </form>
        )}

        <p className="text-center text-xs text-muted-foreground">
          <a href="/sign-in" className="text-primary hover:underline">Back to Sign In</a>
        </p>
      </motion.div>
    </div>
  )
}
