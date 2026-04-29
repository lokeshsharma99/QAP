'use client'
import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import RegistryPage from '@/components/registry/RegistryPage'

export default function Page() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading...</div>}>
      <AppLayout>
        <RegistryPage />
      </AppLayout>
    </Suspense>
  )
}
