import { Suspense } from 'react'
import RegisterPage from '@/components/auth/RegisterPage'
export const metadata = { title: 'Register | Quality Autopilot' }
export default function Page() {
  return <Suspense><RegisterPage /></Suspense>
}
