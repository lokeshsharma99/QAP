import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import AutomationHealthPage from '@/components/automation/AutomationHealthPage'

export const metadata = { title: 'Automation Health | Quality Autopilot' }

export default function AutomationPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading…</div>}>
      <AppLayout>
        <AutomationHealthPage />
      </AppLayout>
    </Suspense>
  )
}
