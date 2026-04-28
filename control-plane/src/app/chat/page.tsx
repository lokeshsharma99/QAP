'use client'
import { Suspense } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import ChatPage from '@/components/chat/ChatPage'

export default function Chat() {
  const hasEnvToken = !!process.env.NEXT_PUBLIC_OS_SECURITY_KEY
  const envToken = process.env.NEXT_PUBLIC_OS_SECURITY_KEY || ''
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-muted text-xs">Loading...</div>}>
      <AppLayout hasEnvToken={hasEnvToken} envToken={envToken}>
        <ChatPage />
      </AppLayout>
    </Suspense>
  )
}
