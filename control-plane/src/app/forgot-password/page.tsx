import { Suspense } from 'react'
import ForgotPasswordPage from '@/components/auth/ForgotPasswordPage'
export const metadata = { title: 'Forgot Password | Quality Autopilot' }
export default function Page() {
  return <Suspense><ForgotPasswordPage /></Suspense>
}
