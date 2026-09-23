import { ChevronDown } from 'lucide-react'
import { ROLE_LABELS } from '../../features/auth/roles'
import { useIdentity } from '../../features/auth/useIdentity'
import { useSignOut } from '../../features/auth/useSignOut'
import type { Role } from '../../types/api'
import { Badge } from '../ui/Badge'
import { Menu, MenuDivider, MenuItem } from '../ui/Menu'
import { InitialsAvatar } from './InitialsAvatar'

interface HeaderProps {
  title: string
  role: Role
}

export function Header({ title, role }: HeaderProps) {
  const identity = useIdentity()
  const signOut = useSignOut()

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-4 border-b border-default bg-surface px-6">
      <h1 className="truncate text-h1 text-primary">{title}</h1>
      <Menu
        label="Account menu"
        trigger={
          <>
            <InitialsAvatar initials={identity.initials} />
            <ChevronDown aria-hidden className="size-4 text-secondary" strokeWidth={1.75} />
          </>
        }
      >
        <div className="px-3 py-2">
          <p className="truncate text-body font-medium text-primary">{identity.name}</p>
          {identity.email && <p className="truncate text-caption text-secondary">{identity.email}</p>}
          <Badge variant="outline-navy" className="mt-2">
            {ROLE_LABELS[role]}
          </Badge>
        </div>
        <MenuDivider />
        <MenuItem onClick={() => void signOut()}>Sign out</MenuItem>
      </Menu>
    </header>
  )
}
