'use client'
import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import EvalsPage from '@/components/evals/EvalsPage'

export default function Page() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading...</div>}>
      <AppLayout>
        <EvalsPage />
      </AppLayout>
    </Suspense>
  )
}
