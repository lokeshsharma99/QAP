import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false },
  // Allow VS Code dev-tunnel origins (*.devtunnels.ms) so the app loads
  // correctly when port-forwarded via VS Code Live Share / Dev Tunnels.
  // Next.js 15 blocks requests whose Host header doesn't match localhost
  // unless explicitly listed here.
  allowedDevOrigins: ['*.devtunnels.ms', 'localhost'],
  async rewrites() {
    return [
      {
        source: '/api/agentOS/:path*',
        destination: `${process.env.NEXT_PUBLIC_AGENTOS_URL || 'http://localhost:8000'}/:path*`
      }
    ]
  }
}

export default nextConfig
