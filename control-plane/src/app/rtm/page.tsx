import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import RTMPage from '@/components/rtm/RTMPage'

export const metadata = { title: 'RTM | Quality Autopilot' }

export default function RTMRoute() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading…</div>}>
      <AppLayout>
        <RTMPage />
      </AppLayout>
    </Suspense>
  )
}
