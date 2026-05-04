'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Loader2, Eye, EyeOff } from 'lucide-react'
import QapLogo from '@/components/auth/QapLogo'
import { toast } from 'sonner'

export default function SignInPage() {
  const router = useRouter()
  const { selectedEndpoint, setAuthToken, setCurrentUser } = useStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  // If already logged in, redirect to chat
  useEffect(() => {
    const token = localStorage.getItem('qap_session_token')
    if (token) router.replace('/chat')
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedEndpoint) { toast.error('No API endpoint configured — check Settings.'); return }
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.AuthLogin(selectedEndpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Login failed.' }))
        throw new Error(err.detail || 'Login failed.')
      }
      const data = await res.json()
      localStorage.setItem('qap_session_token', data.session_token)
      setAuthToken(data.session_token)
      setCurrentUser({ user_id: data.user_id, email: data.email, name: data.name, org_id: data.org_id, role: data.role })
      router.replace('/chat')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Login failed.')
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
        {/* Logo */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center mb-1">
            <QapLogo size={56} />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Quality Autopilot</h1>
            <p className="text-sm text-muted mt-1">Sign in to your organisation</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-card border border-border rounded-2xl p-8 space-y-5 shadow-sm">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Email</label>
            <input
              type="email" required autoFocus
              value={email} onChange={e => setEmail(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
              placeholder="you@company.com"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'} required
                value={password} onChange={e => setPassword(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2.5 pr-10 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                placeholder="••••••••"
              />
              <button type="button" onClick={() => setShowPassword(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            Sign In
          </Button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          Don&apos;t have an account?{' '}
          <a href="/register" className="text-primary hover:underline">Register your organisation</a>
          {' · '}
          <a href="/accept-invite" className="text-primary hover:underline">Accept an invite</a>
          {' · '}
          <a href="/forgot-password" className="text-primary hover:underline">Forgot password?</a>
        </p>
      </motion.div>
    </div>
  )
}
