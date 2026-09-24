import { Building2, LayoutDashboard, Radio, Sparkles, Target, type LucideIcon } from 'lucide-react'
import { NavLink } from 'react-router'
import { ROLE_LABELS } from '../../features/auth/roles'
import { useIdentity } from '../../features/auth/useIdentity'
import { useSignOut } from '../../features/auth/useSignOut'
import { cn } from '../../lib/cn'
import type { Role } from '../../types/api'
import { Badge } from '../ui/Badge'
import { Tooltip } from '../ui/Tooltip'
import { BrandMark } from './BrandMark'
import { InitialsAvatar } from './InitialsAvatar'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/organizations', label: 'Organizations', icon: Building2 },
  { to: '/signals', label: 'Signals', icon: Radio },
  { to: '/opportunities', label: 'Opportunities', icon: Target },
  { to: '/advisor', label: 'AI Advisor', icon: Sparkles },
]

const darkFocus =
  'focus-visible:ring-2 focus-visible:ring-navy-300 focus-visible:ring-offset-2 focus-visible:ring-offset-navy-800 focus-visible:outline-hidden'

export function Sidebar({ role }: { role: Role }) {
  const identity = useIdentity()
  const signOut = useSignOut()
  const roleLabel = ROLE_LABELS[role]

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-18 flex-col border-r border-navy-700 bg-navy-800 xl:w-65">
      <div className="flex h-16 shrink-0 items-center justify-center bg-navy-900 px-3 xl:justify-start xl:px-6">
        <BrandMark tone="dark" collapsible />
      </div>

      <nav aria-label="Primary" className="flex-1 overflow-y-auto pt-6">
        <p className="mb-2 hidden px-6 text-label text-navy-400 uppercase xl:block">Intelligence</p>
        <ul className="space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <Tooltip content={label} wrapperClassName="flex" className="xl:hidden">
                <NavLink
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      'mx-3 flex h-11 flex-1 items-center justify-center gap-3 rounded-md border-l-3 px-3 text-body font-medium',
                      'transition-colors duration-120 ease-out xl:justify-start',
                      isActive
                        ? 'border-indigo-500 bg-navy-900 text-neutral-0'
                        : 'border-transparent text-navy-300 hover:bg-navy-700 hover:text-neutral-0',
                      darkFocus,
                    )
                  }
                >
                  <Icon aria-hidden className="size-5 shrink-0" strokeWidth={1.75} />
                  <span className="sr-only xl:not-sr-only">{label}</span>
                </NavLink>
              </Tooltip>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-navy-700 p-3 xl:p-4">
        <div className="flex items-center justify-center gap-3 xl:justify-start">
          <Tooltip content={`${identity.name} · ${roleLabel}`} className="xl:hidden">
            <InitialsAvatar initials={identity.initials} />
          </Tooltip>
          <div className="hidden min-w-0 flex-1 xl:block">
            <p className="truncate text-body font-medium text-neutral-0">{identity.name}</p>
            <Badge variant="outline-navy-dark" className="mt-1">
              {roleLabel}
            </Badge>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void signOut()}
          className={cn(
            'mt-3 hidden h-9 w-full items-center justify-center rounded-md text-body-sm font-medium text-navy-300',
            'transition-colors duration-120 ease-out hover:bg-navy-700 hover:text-neutral-0 xl:flex',
            darkFocus,
          )}
        >
          Sign out
        </button>
      </div>
    </aside>
  )
}
