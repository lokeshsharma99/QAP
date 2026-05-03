'use client'
import { useCallback, useEffect } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'

const POLL_MS = 30_000

/**
 * Polls pending counts for badge-enabled nav items.
 *
 *   /approvals   — GET /approvals?status=pending  (accurate pending count)
 *   /spec-review — set by SpecReview page itself when it loads
 *   /healing     — set by HealingDashboard page itself when it loads
 *
 * We intentionally do NOT use session-count proxies for spec-review / healing
 * because those return ALL historical sessions (not pending-only), causing false
 * badge counts.
 */
export function usePendingCounts() {
  const { selectedEndpoint, authToken, setPendingCounts } = useStore()

  const fetchCounts = useCallback(async () => {
    if (!selectedEndpoint) return

    const headers: HeadersInit = authToken ? { Authorization: `Bearer ${authToken}` } : {}

    // ── Approvals: filter by status=pending for an accurate count ────────
    try {
      const url = new URL(APIRoutes.GetApprovals(selectedEndpoint))
      url.searchParams.set('status', 'pending')
      url.searchParams.set('limit', '50')
      const res = await fetch(url.toString(), { headers })
      if (res.ok) {
        const data = await res.json()
        const list: unknown[] = data?.data ?? (Array.isArray(data) ? data : [])
        setPendingCounts({ approvals: list.length })
      }
    } catch { /* silent */ }
  }, [selectedEndpoint, authToken, setPendingCounts])

  useEffect(() => {
    fetchCounts()
    const timer = setInterval(fetchCounts, POLL_MS)
    return () => clearInterval(timer)
  }, [fetchCounts])
}
