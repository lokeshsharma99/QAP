export const dynamic = 'force-dynamic'

import AppLayout from '@/components/layout/AppLayout'
import SessionsPage from '@/components/sessions/SessionsPage'

export default function Page() {
  return (
    <AppLayout>
      <SessionsPage />
    </AppLayout>
  )
}
