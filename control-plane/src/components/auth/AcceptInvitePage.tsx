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

export default function AcceptInvitePage() {
  const router = useRouter()
  const params = useSearchParams()
  const { selectedEndpoint, setAuthToken, setCurrentUser } = useStore()
  const [token] = useState(params.get('token') || '')
  const [invite, setInvite] = useState<{ email: string; org_name: string; role: string } | null>(null)
  const [inviteError, setInviteError] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(!!token)

  useEffect(() => {
    if (!token || !selectedEndpoint) return
    setValidating(true)
    fetch(APIRoutes.AuthValidateInvite(selectedEndpoint, token))
      .then(async res => {
        if (!res.ok) throw new Error((await res.json()).detail || 'Invalid invite.')
        return res.json()
      })
      .then(data => setInvite(data))
      .catch(e => setInviteError(e.message))
      .finally(() => setValidating(false))
  }, [token, selectedEndpoint])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { toast.error('Passwords do not match.'); return }
    if (password.length < 8) { toast.error('Password must be at least 8 characters.'); return }
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.AuthAcceptInvite(selectedEndpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, name, password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to accept invite.' }))
        throw new Error(err.detail || 'Failed to accept invite.')
      }
      const data = await res.json()
      localStorage.setItem('qap_session_token', data.session_token)
      setAuthToken(data.session_token)
      setCurrentUser({ user_id: data.user_id, email: data.email, name: data.name, org_id: data.org_id, role: data.role })
      toast.success(`Welcome to ${invite?.org_name || 'Quality Autopilot'}!`)
      router.replace('/chat')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to accept invite.')
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
            <h1 className="text-2xl font-bold">Accept Invitation</h1>
          </div>
        </div>

        {validating && (
          <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground text-sm">
            <Loader2 className="w-4 h-4 animate-spin" /> Validating invite…
          </div>
        )}

        {!validating && inviteError && (
          <div className="flex items-center gap-3 bg-destructive/10 border border-destructive/20 rounded-xl p-4 text-destructive text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{inviteError}</span>
          </div>
        )}

        {!validating && invite && (
          <>
            <div className="flex items-center gap-3 bg-positive/10 border border-positive/20 rounded-xl p-4 text-sm">
              <CheckCircle className="w-5 h-5 text-positive shrink-0" />
              <span>
                You&apos;ve been invited to join <strong>{invite.org_name}</strong> as a{' '}
                <strong>{invite.role}</strong>.
                <br />
                <span className="text-muted-foreground">{invite.email}</span>
              </span>
            </div>

            <form onSubmit={handleSubmit} className="bg-card border border-border rounded-2xl p-8 space-y-4 shadow-sm">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Your Name</label>
                <input
                  type="text" required autoFocus
                  value={name} onChange={e => setName(e.target.value)}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                  placeholder="Jane Smith"
                />
              </div>
              {(['password', 'confirm'] as const).map(k => (
                <div key={k} className="space-y-1.5">
                  <label className="text-sm font-medium">{k === 'password' ? 'Password' : 'Confirm Password'}</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'} required minLength={8}
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
              <Button type="submit" className="w-full mt-2" disabled={loading}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Create Account &amp; Sign In
              </Button>
            </form>
          </>
        )}

        {!token && (
          <div className="bg-card border border-border rounded-2xl p-8 space-y-4 text-center">
            <p className="text-sm text-muted-foreground">
              Paste your invite token below, or click the link in your invitation email.
            </p>
            <input
              type="text"
              placeholder="Paste invite token…"
              className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm outline-none"
              onChange={e => router.replace(`/accept-invite?token=${encodeURIComponent(e.target.value)}`)}
            />
          </div>
        )}

        <p className="text-center text-xs text-muted-foreground">
          Already have an account?{' '}
          <a href="/sign-in" className="text-primary hover:underline">Sign in</a>
        </p>
      </motion.div>
    </div>
  )
}
