'use client'
import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import Dashboard from '@/components/dashboard/Dashboard'

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading...</div>}>
      <AppLayout>
        <Dashboard />
      </AppLayout>
    </Suspense>
  )
}
