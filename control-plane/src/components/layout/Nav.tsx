'use client'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  MessageSquare, LayoutDashboard,
  FileCheck, Wrench, Activity, BookOpen, Brain, ShieldCheck, History, Settings, Map, CalendarClock,
  FlaskConical, Database
} from 'lucide-react'
import { cn } from '@/lib/utils'

type NavEntry =
  | { type: 'link'; href: string; icon: React.ElementType; label: string; badge?: number }
  | { type: 'separator' }

const NAV_ITEMS: NavEntry[] = [
  { type: 'link', href: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { type: 'link', href: '/chat',        icon: MessageSquare,   label: 'Chat' },
  { type: 'link', href: '/sessions',    icon: History,         label: 'Sessions' },
  { type: 'link', href: '/knowledge',   icon: BookOpen,        label: 'Knowledge' },
  { type: 'link', href: '/memory',      icon: Brain,           label: 'Memory' },
  { type: 'link', href: '/traces',      icon: Activity,        label: 'Traces' },
  { type: 'link', href: '/approvals',   icon: ShieldCheck,     label: 'Approvals' },
  { type: 'link', href: '/evals',       icon: FlaskConical,    label: 'Evals' },
  { type: 'link', href: '/registry',    icon: Database,        label: 'Registry' },
  { type: 'link', href: '/spec-review', icon: FileCheck,       label: 'Spec Review' },
  { type: 'link', href: '/healing',     icon: Wrench,          label: 'Healing' },
  { type: 'link', href: '/scheduler',   icon: CalendarClock,   label: 'Scheduler' },
  { type: 'separator' },
  { type: 'link', href: '/guide',       icon: Map,             label: 'Guide' },
  { type: 'separator' },
  { type: 'link', href: '/settings',    icon: Settings,        label: 'Settings' },
]

const NavItem = ({
  href,
  icon: NavIcon,
  label,
  isActive,
  collapsed,
  badge,
}: {
  href: string
  icon: React.ElementType
  label: string
  isActive: boolean
  collapsed: boolean
  badge?: number
}) => (
  <Link href={href} className="relative w-full" title={collapsed ? label : undefined}>
    <div className={cn(
      'flex items-center rounded-xl py-2 text-xs font-medium uppercase transition-colors',
      collapsed ? 'justify-center px-0' : 'gap-3 px-3',
      isActive ? 'bg-accent text-primary' : 'text-muted hover:bg-accent/50 hover:text-primary'
    )}>
      <div className="relative shrink-0">
        <NavIcon className="size-4" />
        {!!badge && (
          <span className="absolute -right-1.5 -top-1.5 flex size-3.5 items-center justify-center rounded-full bg-destructive text-[9px] font-bold text-white">
            {badge > 9 ? '9+' : badge}
          </span>
        )}
      </div>
      {!collapsed && <span className="flex-1">{label}</span>}
      {!collapsed && !!badge && (
        <span className="ml-auto rounded-full bg-destructive/10 px-1.5 py-0.5 text-[10px] font-semibold text-destructive">
          {badge}
        </span>
      )}
      {isActive && (
        <motion.div layoutId="nav-indicator" className="absolute left-0 h-5 w-0.5 rounded-full bg-brand" />
      )}
    </div>
  </Link>
)

const Nav = ({ collapsed = false, approvalCount = 0 }: { collapsed?: boolean; approvalCount?: number }) => {
  const pathname = usePathname()
  return (
    <nav className="flex w-full flex-col gap-0.5 py-1">
      {NAV_ITEMS.map((item, i) => {
        if (item.type === 'separator') {
          return (
            <div key={`sep-${i}`} className={cn('my-1 border-t border-accent/50', collapsed ? 'mx-1' : 'mx-2')} />
          )
        }
        const badge = item.href === '/approvals' ? approvalCount : undefined
        return (
          <NavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={item.label}
            isActive={pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))}
            collapsed={collapsed}
            badge={badge}
          />
        )
      })}
    </nav>
  )
}

export default Nav
