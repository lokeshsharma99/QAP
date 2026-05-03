import { Suspense } from 'react'
import ResetPasswordPage from '@/components/auth/ResetPasswordPage'
export const metadata = { title: 'Reset Password | Quality Autopilot' }
export default function Page() {
  return <Suspense><ResetPasswordPage /></Suspense>
}
