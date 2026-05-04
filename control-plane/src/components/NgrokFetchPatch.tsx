'use client'

/**
 * Patches window.fetch to inject `ngrok-skip-browser-warning: true` on every
 * request whose URL targets an ngrok tunnel domain.
 *
 * ngrok free tier shows a browser-warning interstitial page for requests that
 * look like they come from a browser. The interstitial response lacks
 * Access-Control-Allow-Origin, breaking every cross-origin preflight (CORS).
 * Sending this header bypasses the interstitial unconditionally.
 *
 * This component renders nothing — it only runs the patch once on mount.
 */

import { useEffect } from 'react'

const NGROK_RE = /\.(ngrok-free\.dev|ngrok-free\.app|ngrok\.io)$/

export default function NgrokFetchPatch() {
  useEffect(() => {
    const original = window.fetch
    window.fetch = function (input, init) {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url
      if (NGROK_RE.test(new URL(url, window.location.href).hostname)) {
        const headers = new Headers((init?.headers as HeadersInit | undefined) ?? (input instanceof Request ? input.headers : {}))
        if (!headers.has('ngrok-skip-browser-warning')) {
          headers.set('ngrok-skip-browser-warning', 'true')
        }
        init = { ...init, headers }
      }
      return original.call(this, input, init)
    }
    return () => { window.fetch = original }
  }, [])
  return null
}
