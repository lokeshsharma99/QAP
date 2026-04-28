'use client'
import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import SpecReview from '@/components/spec-review/SpecReview'

export default function SpecReviewPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading...</div>}>
      <AppLayout>
        <SpecReview />
      </AppLayout>
    </Suspense>
  )
}
