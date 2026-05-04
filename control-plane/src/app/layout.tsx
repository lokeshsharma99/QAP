import type { Metadata } from 'next'
import { ThemeProvider } from 'next-themes'
import { NuqsAdapter } from 'nuqs/adapters/next/app'
import { Toaster } from '@/components/ui/sonner'
import NgrokFetchPatch from '@/components/NgrokFetchPatch'
import './globals.css'

export const metadata: Metadata = {
  title: 'Quality Autopilot',
  description: 'Agentic Control Plane for the Software Testing Life Cycle — powered by Agno.'
}

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <NgrokFetchPatch />
          <NuqsAdapter>{children}</NuqsAdapter>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}
