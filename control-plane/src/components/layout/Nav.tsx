'use client'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import {
  MessageSquare, LayoutDashboard,
  FileCheck, Wrench, Activity, BookOpen, Brain, ShieldCheck, History, Settings, Map, CalendarClock,
  FlaskConical, Database, BarChart2, Sparkles, ChevronDown
} from 'lucide-react'
import { cn } from '@/lib/utils'

type NavLink = { type: 'link'; href: string; icon: React.ElementType; label: string }
type NavSection = { type: 'section'; label: string; links: NavLink[] }

const NAV_SECTIONS: NavSection[] = [
  {
    type: 'section', label: 'Core',
    links: [
      { type: 'link', href: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
      { type: 'link', href: '/chat',        icon: MessageSquare,   label: 'Chat' },
      { type: 'link', href: '/sessions',    icon: History,         label: 'Sessions' },
    ],
  },
  {
    type: 'section', label: 'Quality',
    links: [
      { type: 'link', href: '/approvals',   icon: ShieldCheck,     label: 'Approvals' },
      { type: 'link', href: '/spec-review', icon: FileCheck,    label: 'Spec Review' },
      { type: 'link', href: '/healing',     icon: Wrench,       label: 'Healing' },
      { type: 'link', href: '/evals',       icon: FlaskConical, label: 'Evals' },
    ],
  },
  {
    type: 'section', label: 'Insights',
    links: [
      { type: 'link', href: '/traces',  icon: Activity,  label: 'Traces' },
      { type: 'link', href: '/metrics', icon: BarChart2, label: 'Metrics' },
    ],
  },
  {
    type: 'section', label: 'Knowledge',
    links: [
      { type: 'link', href: '/knowledge', icon: BookOpen,  label: 'Knowledge' },
      { type: 'link', href: '/memory',    icon: Brain,     label: 'Memory' },
      { type: 'link', href: '/culture',   icon: Sparkles,  label: 'Culture' },
      { type: 'link', href: '/registry',  icon: Database,  label: 'Registry' },
    ],
  },
  {
    type: 'section', label: 'System',
    links: [
      { type: 'link', href: '/scheduler', icon: CalendarClock, label: 'Scheduler' },
      { type: 'link', href: '/guide',     icon: Map,           label: 'Guide' },
      { type: 'link', href: '/settings',  icon: Settings,      label: 'Settings' },
    ],
  },
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

const NavSectionGroup = ({
  section,
  sidebarCollapsed,
  open,
  onToggle,
  pathname,
  approvalCount,
}: {
  section: NavSection
  sidebarCollapsed: boolean
  open: boolean
  onToggle: () => void
  pathname: string
  approvalCount: number
}) => {
  if (sidebarCollapsed) {
    return (
      <>
        <div className="mx-1 my-1.5 border-t border-accent/50" />
        {section.links.map((link) => (
          <NavItem
            key={link.href}
            href={link.href}
            icon={link.icon}
            label={link.label}
            isActive={pathname === link.href || (link.href !== '/dashboard' && pathname.startsWith(link.href))}
            collapsed
            badge={link.href === '/approvals' ? approvalCount : undefined}
          />
        ))}
      </>
    )
  }

  return (
    <div className="mt-1">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-1 px-3 py-0.5 text-[9px] font-semibold uppercase tracking-widest text-muted/60 hover:text-muted transition-colors"
      >
        <span className="flex-1 text-left">{section.label}</span>
        <ChevronDown
          className={cn('size-2.5 transition-transform duration-200', open ? 'rotate-0' : '-rotate-90')}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            {section.links.map((link) => (
              <NavItem
                key={link.href}
                href={link.href}
                icon={link.icon}
                label={link.label}
                isActive={pathname === link.href || (link.href !== '/dashboard' && pathname.startsWith(link.href))}
                collapsed={false}
                badge={link.href === '/approvals' ? approvalCount : undefined}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const Nav = ({ collapsed = false, approvalCount = 0 }: { collapsed?: boolean; approvalCount?: number }) => {
  const pathname = usePathname()
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({ Core: true })

  const toggle = (label: string) =>
    setOpenSections((prev) => ({ ...prev, [label]: !prev[label] }))

  return (
    <nav className="flex w-full flex-col gap-0.5 py-1">
      {NAV_SECTIONS.map((section) => (
        <NavSectionGroup
          key={section.label}
          section={section}
          sidebarCollapsed={collapsed}
          open={!!openSections[section.label]}
          onToggle={() => toggle(section.label)}
          pathname={pathname}
          approvalCount={approvalCount}
        />
      ))}
    </nav>
  )
}

export default Nav
