import { useUser } from '@clerk/react'

export interface Identity {
  name: string
  email: string | null
  initials: string
  clerkUserId: string | null
}

function initialsFrom(text: string): string {
  const parts = text.split(/[\s@._-]+/).filter(Boolean)
  const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : text.slice(0, 2)
  return letters.toUpperCase()
}

export function useIdentity(): Identity {
  const { user } = useUser()
  const email = user?.primaryEmailAddress?.emailAddress ?? null
  const name = user?.fullName?.trim() || email || 'Signed-in user'
  return { name, email, initials: initialsFrom(name), clerkUserId: user?.id ?? null }
}
