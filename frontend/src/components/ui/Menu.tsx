import { useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface MenuProps {
  label: string
  trigger: ReactNode
  children: ReactNode
  className?: string
}

export function Menu({ label, trigger, children, className }: MenuProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelId = useId()

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    rootRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus()
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div ref={rootRef} className={cn('relative', className)}>
      <button
        ref={triggerRef}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1 rounded-full focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:outline-hidden"
      >
        {trigger}
      </button>
      {open && (
        <div
          id={panelId}
          role="menu"
          onClick={(event) => {
            if ((event.target as HTMLElement).closest('[role="menuitem"]')) setOpen(false)
          }}
          className="absolute right-0 z-40 mt-1 w-72 rounded-md border border-default bg-surface p-1 shadow-md"
        >
          {children}
        </div>
      )}
    </div>
  )
}

export function MenuItem({ className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      role="menuitem"
      className={cn(
        'flex h-9 w-full items-center rounded-sm px-3 text-left text-body text-primary',
        'hover:bg-surface-sunken focus-visible:bg-surface-sunken focus-visible:outline-hidden',
        className,
      )}
      {...rest}
    />
  )
}

export function MenuDivider() {
  return <div role="separator" className="my-1 border-t border-default" />
}
