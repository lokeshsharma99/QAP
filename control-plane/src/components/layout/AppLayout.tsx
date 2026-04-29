'use client'
import { useEffect, useState, useCallback } from 'react'
import { useTheme } from 'next-themes'
import { useStore } from '@/store'
import useChatActions from '@/hooks/useChatActions'
import Nav from './Nav'
import Icon from '@/components/ui/icon'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { PanelLeftClose, PanelLeftOpen, Sun, Moon, Monitor } from 'lucide-react'
import { APIRoutes } from '@/api/routes'

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
  const { setAuthToken, authToken, navCollapsed, setNavCollapsed, selectedEndpoint } = useStore()
  const { initialize } = useChatActions()
  const [approvalCount, setApprovalCount] = useState(0)

  const pollApprovals = useCallback(async () => {
    if (!selectedEndpoint) return
    try {
      const headers: Record<string, string> = authToken ? { Authorization: `Bearer ${authToken}` } : {}
      const res = await fetch(APIRoutes.ApprovalCount(selectedEndpoint), { headers })
      if (res.ok) {
        const data = await res.json()
        setApprovalCount(data?.pending ?? data?.count ?? 0)
      }
    } catch { /* silent */ }
  }, [selectedEndpoint, authToken])

  useEffect(() => {
    if (hasEnvToken && envToken && !authToken) {
      setAuthToken(envToken)
    }
    initialize()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    pollApprovals()
    const timer = setInterval(pollApprovals, 30_000)
    return () => clearInterval(timer)
  }, [pollApprovals])

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
              <Icon type="agno" size="xs" />
              <span className="text-xs font-medium uppercase text-white">Quality Autopilot</span>
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
          <Nav collapsed={navCollapsed} approvalCount={approvalCount} />
        </div>

        {/* Theme toggle — pinned to sidebar bottom */}
        <div className="border-t border-accent/50 px-1 pt-1.5">
          <ThemeToggle collapsed={navCollapsed} />
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

