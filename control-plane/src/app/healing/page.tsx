'use client'
import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import HealingDashboard from '@/components/healing/HealingDashboard'

export default function HealingPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading...</div>}>
      <AppLayout>
        <HealingDashboard />
      </AppLayout>
    </Suspense>
  )
}
