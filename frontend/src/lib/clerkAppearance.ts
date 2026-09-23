export const clerkAppearance = {
  options: {
    logoPlacement: 'none' as const,
  },
  variables: {
    colorPrimary: '#1e3a66',
    colorPrimaryForeground: '#ffffff',
    colorDanger: '#dc2626',
    colorSuccess: '#059669',
    colorWarning: '#d97706',
    colorNeutral: '#0f172a',
    colorForeground: '#0f172a',
    colorMutedForeground: '#64748b',
    colorBackground: '#ffffff',
    colorInput: '#ffffff',
    colorInputForeground: '#0f172a',
    colorBorder: '#e2e8f0',
    colorRing: '#4e6b9b',
    colorShadow: '#0f172a',
    fontFamily: "Inter, -apple-system, 'Segoe UI', Roboto, sans-serif",
    fontSize: '0.875rem',
    borderRadius: '6px',
  },
  elements: {
    rootBox: { width: '100%' },
    cardBox: {
      width: '100%',
      boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
      border: '1px solid #e2e8f0',
      borderRadius: '12px',
    },
  },
}
