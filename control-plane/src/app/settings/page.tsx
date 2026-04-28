export const dynamic = 'force-dynamic'
import AppLayout from '@/components/layout/AppLayout'
import SettingsPage from '@/components/settings/SettingsPage'

export default function Page() {
  return <AppLayout><SettingsPage /></AppLayout>
}
