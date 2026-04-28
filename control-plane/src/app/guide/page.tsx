'use client'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

export default function GuidePage() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top bar with back button */}
      <div className="flex shrink-0 items-center gap-3 border-b border-accent/50 px-4 py-2.5">
        <Link
          href="/dashboard"
          className="flex items-center gap-1.5 text-xs text-muted transition-colors hover:text-primary"
        >
          <ArrowLeft className="size-3.5" />
          Back
        </Link>
        <span className="text-xs font-medium text-primary">System Guide</span>
      </div>

      {/* Full-height iframe */}
      <iframe
        src="/system-guide.html"
        className="flex-1 w-full border-0"
        title="Quality Autopilot System Guide"
      />
    </div>
  )
}
