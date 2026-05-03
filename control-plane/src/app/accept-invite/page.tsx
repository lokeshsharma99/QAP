import { Suspense } from 'react'
import AcceptInvitePage from '@/components/auth/AcceptInvitePage'
export const metadata = { title: 'Accept Invitation | Quality Autopilot' }
export default function Page() {
  return <Suspense><AcceptInvitePage /></Suspense>
}
