'use client'
import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'
import { Loader2, Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react'
import QapLogo from '@/components/auth/QapLogo'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

type OrgStatus = 'idle' | 'checking' | 'found' | 'not_found'

export default function RegisterPage() {
  const router = useRouter()
  const { selectedEndpoint, setAuthToken, setCurrentUser } = useStore()
  const [form, setForm] = useState({ orgName: '', name: '', email: '', password: '', confirm: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [orgStatus, setOrgStatus] = useState<OrgStatus>('idle')
  const [resolvedOrgName, setResolvedOrgName] = useState('')

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [k]: e.target.value }))
    if (k === 'orgName') { setOrgStatus('idle'); setResolvedOrgName('') }
  }

  const lookupOrg = useCallback(async () => {
    if (!form.orgName.trim() || !selectedEndpoint) return
    setOrgStatus('checking')
    try {
      const res = await fetch(APIRoutes.AuthOrgLookup(selectedEndpoint, form.orgName.trim()))
      if (res.ok) {
        const data = await res.json()
        setOrgStatus('found')
        setResolvedOrgName(data.org_name)
      } else {
        setOrgStatus('not_found')
        setResolvedOrgName('')
      }
    } catch {
      setOrgStatus('not_found')
      setResolvedOrgName('')
    }
  }, [form.orgName, selectedEndpoint])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (orgStatus !== 'found') { toast.error('Organisation not found. Check the name and try again.'); return }
    if (form.password !== form.confirm) { toast.error('Passwords do not match.'); return }
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters.'); return }
    if (!selectedEndpoint) { toast.error('No API endpoint configured — check Settings.'); return }
    setLoading(true)
    try {
      const res = await fetch(APIRoutes.AuthRegister(selectedEndpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org_name: form.orgName.trim(), name: form.name, email: form.email, password: form.password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Registration failed.' }))
        throw new Error(err.detail || 'Registration failed.')
      }
      const data = await res.json()
      localStorage.setItem('qap_session_token', data.session_token)
      setAuthToken(data.session_token)
      setCurrentUser({ user_id: data.user_id, email: data.email, name: data.name, org_id: data.org_id, role: data.role })
      toast.success(`Welcome to ${resolvedOrgName || form.orgName}!`)
      router.replace('/chat')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  const orgStatusIcon = {
    idle: null,
    checking: <Loader2 className="size-4 animate-spin text-muted" />,
    found: <CheckCircle2 className="size-4 text-positive" />,
    not_found: <AlertCircle className="size-4 text-destructive" />,
  }[orgStatus]

  const orgStatusMsg = {
    idle: null,
    checking: <span className="text-muted">Checking…</span>,
    found: <span className="text-positive">Organisation found: <strong>{resolvedOrgName}</strong></span>,
    not_found: <span className="text-destructive">Organisation not found. Ask your admin to create it.</span>,
  }[orgStatus]

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
            <h1 className="text-2xl font-bold">Join Your Organisation</h1>
            <p className="text-sm text-muted mt-1">Enter your organisation name to get started</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="bg-primaryAccent border border-accent rounded-2xl p-8 space-y-4 shadow-sm">
          {/* Org name with lookup */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-primary">Organisation Name</label>
            <div className="relative">
              <input
                type="text" required autoFocus
                value={form.orgName}
                onChange={set('orgName')}
                onBlur={lookupOrg}
                className={cn(
                  'w-full bg-background border rounded-lg px-3 py-2.5 pr-10 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition',
                  orgStatus === 'found' ? 'border-positive/50' : orgStatus === 'not_found' ? 'border-destructive/50' : 'border-accent'
                )}
                placeholder="Acme QA Team"
              />
              {orgStatusIcon && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2">{orgStatusIcon}</span>
              )}
            </div>
            {orgStatusMsg && <p className="text-xs">{orgStatusMsg}</p>}
          </div>

          {/* Name + Email */}
          {([
            { key: 'name',  label: 'Your Name', type: 'text',  placeholder: 'Jane Smith' },
            { key: 'email', label: 'Email',      type: 'email', placeholder: 'you@company.com' },
          ] as const).map(({ key, label, type, placeholder }) => (
            <div key={key} className="space-y-1.5">
              <label className="text-sm font-medium text-primary">{label}</label>
              <input
                type={type} required
                value={form[key]}
                onChange={set(key)}
                className="w-full bg-background border border-accent rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition placeholder:text-muted"
                placeholder={placeholder}
              />
            </div>
          ))}

          {/* Password */}
          {(['password', 'confirm'] as const).map(k => (
            <div key={k} className="space-y-1.5">
              <label className="text-sm font-medium text-primary">{k === 'password' ? 'Password' : 'Confirm Password'}</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'} required minLength={8}
                  value={form[k]} onChange={set(k)}
                  className="w-full bg-background border border-accent rounded-lg px-3 py-2.5 pr-10 text-sm outline-none focus:ring-2 focus:ring-primary/30 transition"
                  placeholder="••••••••"
                />
                {k === 'password' && (
                  <button type="button" onClick={() => setShowPassword(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-primary">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                )}
              </div>
            </div>
          ))}

          <Button
            type="submit"
            className="w-full mt-2"
            disabled={loading || orgStatus !== 'found'}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            Join Organisation
          </Button>
        </form>

        <p className="text-center text-xs text-muted">
          Already have an account?{' '}
          <a href="/sign-in" className="text-primary hover:underline">Sign in</a>
          {' · '}
          <a href="/accept-invite" className="text-primary hover:underline">Accept an invite</a>
        </p>
      </motion.div>
    </div>
  )
}
