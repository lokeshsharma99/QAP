'use client'
import { useRef, useEffect } from 'react'
import { useTheme } from 'next-themes'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

export default function GuidePage() {
  const { resolvedTheme } = useTheme()
  const iframeRef = useRef<HTMLIFrameElement>(null)

  // Push theme into the iframe whenever it changes
  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return
    const send = () => {
      iframe.contentWindow?.postMessage({ theme: resolvedTheme ?? 'dark' }, '*')
    }
    // Send on load
    iframe.addEventListener('load', send)
    // Also send immediately if already loaded
    send()
    return () => iframe.removeEventListener('load', send)
  }, [resolvedTheme])

  return (
    <div className="absolute inset-0 flex flex-col overflow-hidden">
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

      {/* Full-height iframe — flex-1 + min-h-0 forces flex to own the height */}
      <iframe
        ref={iframeRef}
        src="/system-guide.html"
        className="min-h-0 w-full flex-1 border-0"
        title="Quality Autopilot System Guide"
        loading="lazy"
      />
    </div>
  )
}
