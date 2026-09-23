import { Building2, Radio, Sparkles, Target } from 'lucide-react'
import { Route, Routes } from 'react-router'
import { LoginPage } from '../features/auth/LoginPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { NotFoundPage } from './NotFoundPage'
import { PendingPage } from './PendingPage'
import { RequireAuth } from './RequireAuth'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login/*" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<DashboardPage />} />
        <Route path="organizations" element={<PendingPage icon={Building2} name="Organizations" />} />
        <Route path="signals" element={<PendingPage icon={Radio} name="Signals" />} />
        <Route path="opportunities" element={<PendingPage icon={Target} name="Potential Opportunities" />} />
        <Route path="advisor" element={<PendingPage icon={Sparkles} name="AI Sales Advisor" />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
