'use client'
import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import WorkflowsPanel from '@/components/workflows/WorkflowsPanel'

export default function WorkflowsPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading...</div>}>
      <AppLayout>
        <WorkflowsPanel />
      </AppLayout>
    </Suspense>
  )
}
