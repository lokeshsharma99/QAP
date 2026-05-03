import { Suspense } from 'react'
import SignInPage from '@/components/auth/SignInPage'
export const metadata = { title: 'Sign In | Quality Autopilot' }
export default function Page() {
  return <Suspense><SignInPage /></Suspense>
}
