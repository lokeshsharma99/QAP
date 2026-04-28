import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false },
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
