import { Route, Routes } from 'react-router'
import { LoginPage } from '../features/auth/LoginPage'
import { AdvisorPage } from '../features/advisor/AdvisorPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { OrganizationDetailPage } from '../features/organizations/OrganizationDetailPage'
import { OrganizationsPage } from '../features/organizations/OrganizationsPage'
import { OpportunitiesPage } from '../features/opportunities/OpportunitiesPage'
import { OpportunityDetailPage } from '../features/opportunities/OpportunityDetailPage'
import { SignalDetailPage } from '../features/signals/SignalDetailPage'
import { SignalsPage } from '../features/signals/SignalsPage'
import { NotFoundPage } from './NotFoundPage'
import { RequireAuth } from './RequireAuth'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login/*" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<DashboardPage />} />
        <Route path="organizations" element={<OrganizationsPage />} />
        <Route path="organizations/:organizationId" element={<OrganizationDetailPage />} />
        <Route path="signals" element={<SignalsPage />} />
        <Route path="signals/:signalId" element={<SignalDetailPage />} />
        <Route path="opportunities" element={<OpportunitiesPage />} />
        <Route path="opportunities/:opportunityId" element={<OpportunityDetailPage />} />
        <Route path="advisor" element={<AdvisorPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
