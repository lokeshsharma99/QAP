export const dynamic = 'force-dynamic'
import AppLayout from '@/components/layout/AppLayout'
import MetricsPage from '@/components/metrics/MetricsPage'

export default function Page() {
  return <AppLayout><MetricsPage /></AppLayout>
}
