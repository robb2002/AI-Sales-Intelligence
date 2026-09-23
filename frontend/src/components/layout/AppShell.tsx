import { Outlet, useLocation } from 'react-router'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import type { CurrentUser } from '../../types/api'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Intelligence Command Center',
  '/organizations': 'Organizations',
  '/signals': 'Signals',
  '/opportunities': 'Potential Opportunities',
  '/advisor': 'AI Sales Advisor',
}

export function AppShell({ user }: { user: CurrentUser }) {
  const { pathname } = useLocation()
  const title = ROUTE_TITLES[pathname] ?? 'Page not found'
  useDocumentTitle(title)

  return (
    <div className="min-h-screen bg-app">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-70 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2 focus:text-body focus:font-medium focus:text-navy-600 focus:shadow-md"
      >
        Skip to content
      </a>
      <Sidebar role={user.role} />
      <div className="ml-18 flex min-h-screen flex-col xl:ml-65">
        <Header title={title} role={user.role} />
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-360 flex-1 px-8 py-8 focus:outline-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
