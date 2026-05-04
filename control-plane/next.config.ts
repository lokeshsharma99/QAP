import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false },
  // Allow VS Code dev-tunnel and ngrok origins for Server Actions (production).
  // Also allows the dev server to accept requests from these origins.
  // Note: if the page still returns 502 after a container rebuild, stop and
  // re-forward the port in VS Code's Ports panel — the tunnel connection
  // drops when the container restarts and must be re-established manually.
  experimental: {
    serverActions: {
      allowedOrigins: [
        '*.devtunnels.ms',
        '*.ngrok.io',
        '*.ngrok-free.app',
        '*.ngrok-free.dev',
        '*.trycloudflare.com',
      ],
    },
  },
  async rewrites() {
    return [
      {
        source: '/api/agentOS/:path*',
        // Use AGENTOS_URL (server-only runtime var) for Docker-internal routing.
        // Falls back to NEXT_PUBLIC_AGENTOS_URL then localhost for local dev.
        destination: `${process.env.AGENTOS_URL || process.env.NEXT_PUBLIC_AGENTOS_URL || 'http://localhost:8000'}/:path*`
      }
    ]
  }
}

export default nextConfig
