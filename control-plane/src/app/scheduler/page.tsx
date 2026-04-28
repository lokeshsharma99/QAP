'use client'
import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import SchedulerPage from '@/components/scheduler/SchedulerPage'

export default function Page() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading...</div>}>
      <AppLayout>
        <SchedulerPage />
      </AppLayout>
    </Suspense>
  )
}
