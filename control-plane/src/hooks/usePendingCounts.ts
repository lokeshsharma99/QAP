'use client'
import { useCallback, useEffect } from 'react'
import { useStore } from '@/store'
import { APIRoutes } from '@/api/routes'

const DB_ID = 'quality-autopilot-db'
const POLL_MS = 30_000

/**
 * Polls pending counts for the three badge-enabled nav items:
 *   /approvals   — from GET /approvals/count  (Agno native)
 *   /spec-review — from scribe agent sessions total (proxy for items needing review)
 *   /healing     — from medic agent sessions total  (proxy for patches needing review)
 *
 * Individual pages (SpecReview, HealingDashboard) call setPendingCounts with the
 * real "pending" count once they parse their session messages, overwriting the proxy.
 */
export function usePendingCounts() {
  const { selectedEndpoint, authToken, setPendingCounts } = useStore()

  const fetchCounts = useCallback(async () => {
    if (!selectedEndpoint) return

    const headers: HeadersInit = authToken ? { Authorization: `Bearer ${authToken}` } : {}

    // ── 1. Approvals (Agno native endpoint) ──────────────────────────────
    const fetchApprovals = async () => {
      try {
        const res = await fetch(APIRoutes.ApprovalCount(selectedEndpoint), { headers })
        if (res.ok) {
          const data = await res.json()
          return (data?.pending ?? data?.count ?? 0) as number
        }
      } catch { /* silent */ }
      return 0
    }

    // ── 2. Spec Review — count scribe sessions as proxy ──────────────────
    const fetchSpecReview = async () => {
      try {
        const url = new URL(APIRoutes.GetSessions(selectedEndpoint))
        url.searchParams.set('type', 'agent')
        url.searchParams.set('component_id', 'scribe')
        url.searchParams.set('db_id', DB_ID)
        const res = await fetch(url.toString(), { headers })
        if (res.ok) {
          const data = await res.json()
          const sessions: unknown[] = data?.data ?? (Array.isArray(data) ? data : [])
          return sessions.length
        }
      } catch { /* silent */ }
      return 0
    }

    // ── 3. Healing — count medic sessions as proxy ───────────────────────
    const fetchHealing = async () => {
      try {
        const url = new URL(APIRoutes.GetSessions(selectedEndpoint))
        url.searchParams.set('type', 'agent')
        url.searchParams.set('component_id', 'medic')
        url.searchParams.set('db_id', DB_ID)
        const res = await fetch(url.toString(), { headers })
        if (res.ok) {
          const data = await res.json()
          const sessions: unknown[] = data?.data ?? (Array.isArray(data) ? data : [])
          return sessions.length
        }
      } catch { /* silent */ }
      return 0
    }

    const [approvals, specReview, healing] = await Promise.all([
      fetchApprovals(),
      fetchSpecReview(),
      fetchHealing(),
    ])

    setPendingCounts({ approvals, specReview, healing })
  }, [selectedEndpoint, authToken, setPendingCounts])

  useEffect(() => {
    fetchCounts()
    const timer = setInterval(fetchCounts, POLL_MS)
    return () => clearInterval(timer)
  }, [fetchCounts])
}
