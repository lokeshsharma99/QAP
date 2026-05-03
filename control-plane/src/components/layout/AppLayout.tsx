'use client'
import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import { useRouter } from 'next/navigation'
import { useStore } from '@/store'
import useChatActions from '@/hooks/useChatActions'
import Nav from './Nav'
import Icon from '@/components/ui/icon'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { PanelLeftClose, PanelLeftOpen, Sun, Moon, Monitor, LogOut, User } from 'lucide-react'
import { APIRoutes } from '@/api/routes'
import { usePendingCounts } from '@/hooks/usePendingCounts'

interface AppLayoutProps {
  children: React.ReactNode
  hasEnvToken?: boolean
  envToken?: string
}

// ---------------------------------------------------------------------------
// Theme toggle — cycles system → dark → light
// ---------------------------------------------------------------------------
const THEME_CYCLE = ['system', 'dark', 'light'] as const
type ThemeOption = typeof THEME_CYCLE[number]

const ThemeToggle = ({ collapsed }: { collapsed: boolean }) => {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])
  if (!mounted) return null

  const cycle = () => {
    const idx = THEME_CYCLE.indexOf(theme as ThemeOption)
    setTheme(THEME_CYCLE[(idx + 1) % THEME_CYCLE.length])
  }

  const Icon = theme === 'dark' ? Moon : theme === 'light' ? Sun : Monitor
  const label = theme === 'dark' ? 'Dark' : theme === 'light' ? 'Light' : 'System'

  return (
    <button
      onClick={cycle}
      title={`Theme: ${label} — click to cycle`}
      className={cn(
        'flex items-center rounded-xl py-2 text-xs font-medium uppercase text-muted transition-colors hover:bg-accent/50 hover:text-primary',
        collapsed ? 'w-full justify-center px-0' : 'gap-3 px-3'
      )}
    >
      <Icon className="size-4 shrink-0" />
      {!collapsed && <span>{label}</span>}
    </button>
  )
}

// ---------------------------------------------------------------------------
// User chip + logout button
// ---------------------------------------------------------------------------
const UserChip = ({ collapsed }: { collapsed: boolean }) => {
  const { currentUser, setCurrentUser, setAuthToken, selectedEndpoint, authToken } = useStore()
  const router = useRouter()

  const handleLogout = async () => {
    try {
      if (selectedEndpoint) {
        await fetch(APIRoutes.AuthLogout(selectedEndpoint), {
          method: 'POST',
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        })
      }
    } catch { /* ignore */ }
    localStorage.removeItem('qap_session_token')
    setAuthToken('')
    setCurrentUser(null)
    router.replace('/sign-in')
  }

  if (!currentUser) return null
  return (
    <div className={cn(
      'flex items-center rounded-xl py-1.5 text-xs text-muted',
      collapsed ? 'justify-center px-0' : 'gap-2 px-2'
    )}>
      <User className="size-3.5 shrink-0 text-muted-foreground" />
      {!collapsed && (
        <span className="flex-1 truncate text-muted-foreground">{currentUser.name || currentUser.email}</span>
      )}
      <button
        onClick={handleLogout}
        title="Sign out"
        className="text-muted-foreground hover:text-destructive transition-colors"
      >
        <LogOut className="size-3.5" />
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Compact endpoint status chip shown in sidebar
// ---------------------------------------------------------------------------
const EndpointChip = ({ collapsed }: { collapsed: boolean }) => {
  const { selectedEndpoint, isEndpointActive, isEndpointLoading } = useStore()

  const dotClass = cn(
    'size-2 shrink-0 rounded-full',
    isEndpointLoading ? 'animate-pulse bg-warning' :
      isEndpointActive ? 'bg-positive' : 'bg-destructive'
  )

  return (
    <Link
      href="/settings"
      title="Open Settings to configure the AgentOS endpoint"
      className={cn(
        'flex items-center gap-2 rounded-xl border border-primary/10 bg-accent px-3 py-1.5 text-xs text-muted transition-colors hover:border-primary/30 hover:text-primary',
        collapsed && 'justify-center px-0 py-1.5'
      )}
    >
      <span className={dotClass} />
      {!collapsed && (
        <span className="flex-1 truncate">
          {selectedEndpoint.replace(/^https?:\/\//, '')}
        </span>
      )}
    </Link>
  )
}

// ---------------------------------------------------------------------------
// AppLayout
// ---------------------------------------------------------------------------
const AppLayout = ({ children, hasEnvToken = false, envToken = '' }: AppLayoutProps) => {
  const { setAuthToken, setCurrentUser, authToken, navCollapsed, setNavCollapsed, selectedEndpoint, pendingCounts } = useStore()
  const { initialize } = useChatActions()
  const router = useRouter()

  // Live badge counts for Approvals, Spec Review, Healing
  usePendingCounts()

  useEffect(() => {
    // Restore token: env var wins, then localStorage
    const stored = localStorage.getItem('qap_session_token')
    const token = (hasEnvToken && envToken) ? envToken : (stored || '')
    if (token && !authToken) {
      setAuthToken(token)
    }

    // No token at all → redirect to sign-in immediately
    if (!token) {
      router.replace('/sign-in')
      return
    }

    // Validate session with /auth/me and hydrate currentUser
    if (token && selectedEndpoint) {
      fetch(APIRoutes.AuthMe(selectedEndpoint), {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(async res => {
          if (res.status === 401) {
            localStorage.removeItem('qap_session_token')
            setAuthToken('')
            setCurrentUser(null)
            router.replace('/sign-in')
          } else if (res.ok) {
            const user = await res.json()
            setCurrentUser(user)
          }
        })
        .catch(() => { /* offline — don't redirect */ })
    }
    initialize()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Build badge map for Nav
  const navBadges: Record<string, number> = {}
  if (pendingCounts.approvals  > 0) navBadges['/approvals']   = pendingCounts.approvals
  if (pendingCounts.specReview > 0) navBadges['/spec-review'] = pendingCounts.specReview
  if (pendingCounts.healing    > 0) navBadges['/healing']     = pendingCounts.healing

  return (
    <div className="flex h-screen overflow-hidden bg-background/80">
      {/* Sidebar */}
      <aside
        className={cn(
          'flex shrink-0 flex-col bg-primaryAccent transition-all duration-200',
          navCollapsed ? 'w-12 p-1.5' : 'w-52 gap-3 p-3'
        )}
      >
        {/* Brand + collapse toggle */}
        <div className={cn('flex items-center', navCollapsed ? 'justify-center py-1' : 'justify-between px-1 pt-1')}>
          {!navCollapsed && (
            <div className="flex items-center gap-2">
              <Icon type="qap" size="xs" />
              <span className="text-xs font-medium uppercase text-primary">Quality Autopilot</span>
            </div>
          )}
          <button
            onClick={() => setNavCollapsed(!navCollapsed)}
            title={navCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={cn(
              'rounded-lg p-1 text-muted hover:bg-accent/50 hover:text-primary transition-colors',
              navCollapsed && 'mx-auto'
            )}
          >
            {navCollapsed
              ? <PanelLeftOpen className="size-4" />
              : <PanelLeftClose className="size-4" />
            }
          </button>
        </div>

        {/* Navigation — flex-1 pushes theme toggle to bottom */}
        <div className="flex-1 overflow-y-auto">
          <Nav collapsed={navCollapsed} pendingCounts={navBadges} />
        </div>

        {/* Theme toggle — pinned to sidebar bottom */}
        <div className="border-t border-accent/50 px-1 pt-1.5 space-y-1">
          <ThemeToggle collapsed={navCollapsed} />
          <UserChip collapsed={navCollapsed} />
        </div>
      </aside>

      {/* Main content */}
      <main className="relative m-1.5 flex flex-grow flex-col overflow-hidden rounded-xl bg-background">
        {children}
      </main>
    </div>
  )
}

export default AppLayout

