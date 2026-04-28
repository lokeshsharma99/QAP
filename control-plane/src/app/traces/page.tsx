export const dynamic = 'force-dynamic'
import AppLayout from '@/components/layout/AppLayout'
import TracesPage from '@/components/traces/TracesPage'

export default function Page() {
  return <AppLayout><TracesPage /></AppLayout>
}
