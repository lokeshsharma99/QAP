'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Loader2, Eye, EyeOff, Zap } from 'lucide-react'
import { toast } from 'sonner'

export default function RegisterPage() {
  const router = useRouter()
  const { selectedEndpoint, setAuthToken, setCurrentUser } = useStore()
  const [form, setForm] = useState({ orgName: '', name: '', email: '', password: '', confirm: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(prev => ({ ...prev, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirm) { toast.error('Passwords do not match.'); return }
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters.'); return }
    if (!selectedEndpoint) { toast.error('No API endpoint configured — check Settings.'); return }
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.AuthRegister(selectedEndpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org_name: form.orgName, name: form.name, email: form.email, password: form.password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Registration failed.' }))
        throw new Error(err.detail || 'Registration failed.')
      }
      const data = await res.json()
      localStorage.setItem('qap_session_token', data.session_token)
      setAuthToken(data.session_token)
      setCurrentUser({ user_id: data.user_id, email: data.email, name: data.name, org_id: data.org_id, role: data.role })
      toast.success('Organisation created! Welcome to Quality Autopilot.')
      router.replace('/chat')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Registration failed.')
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
          <h1 className="text-2xl font-bold">Create Organisation</h1>
          <p className="text-sm text-muted-foreground">Set up your team&apos;s Quality Autopilot workspace</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-card border border-border rounded-2xl p-8 space-y-4 shadow-sm">
          {[
            { key: 'orgName', label: 'Organisation Name', type: 'text', placeholder: 'Acme QA Team' },
            { key: 'name',    label: 'Your Name',         type: 'text', placeholder: 'Jane Smith' },
            { key: 'email',   label: 'Email',             type: 'email', placeholder: 'you@company.com' },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key} className="space-y-1.5">
              <label className="text-sm font-medium">{label}</label>
              <input
                type={type} required autoFocus={key === 'orgName'}
                value={form[key as keyof typeof form]}
                onChange={set(key as keyof typeof form)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                placeholder={placeholder}
              />
            </div>
          ))}
          {(['password', 'confirm'] as const).map(k => (
            <div key={k} className="space-y-1.5">
              <label className="text-sm font-medium">{k === 'password' ? 'Password' : 'Confirm Password'}</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'} required minLength={8}
                  value={form[k]} onChange={set(k)}
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
            Create Organisation
          </Button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          Already have an account?{' '}
          <a href="/sign-in" className="text-primary hover:underline">Sign in</a>
          {' · '}
          <a href="/accept-invite" className="text-primary hover:underline">Accept an invite</a>
        </p>
      </motion.div>
    </div>
  )
}
