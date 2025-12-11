// Design Tokens per Vertigo HR
// Mantiene sincronizzazione con CSS variables in styles.css

export const colors = {
  // Primary Purple
  primaryPurple: '#7C3AED',
  primaryHover: '#6D28D9',
  primaryLight: '#A78BFA',
  
  // Accent Colors
  accentPurple: '#A78BFA',
  accentPink: '#F0ABFC',
  
  // Gradients
  gradientPrimary: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
  gradientSurface: 'linear-gradient(145deg, #F5F3FF 0%, #FCE7F3 100%)',
  
  // Surface & Background
  surfaceGlass: 'rgba(255, 255, 255, 0.7)',
  bgPrimary: '#FFFFFF',
  bgSecondary: '#F9FAFB',
  lightPurple: '#F3F0FF',
  pastelPink: '#FDF2F8',
  
  // Text Colors
  textPrimary: '#1F2937',
  textSecondary: '#6B7280',
  textMuted: '#9CA3AF',
  
  // Border & Dividers
  borderLight: '#E5E7EB',
  
  // Status Colors
  success: '#10B981',
  successLight: '#D1FAE5',
  warning: '#F59E0B',
  warningLight: '#FEF3C7',
  error: '#EF4444',
  errorLight: '#FEE2E2',
  info: '#3B82F6',
  infoLight: '#DBEAFE',
} as const

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  '2xl': '48px',
  '3xl': '64px',
} as const

export const radius = {
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '20px',
  full: '9999px',
} as const

export const shadows = {
  sm: '0 2px 8px rgba(124, 58, 237, 0.06)',
  md: '0 4px 16px rgba(124, 58, 237, 0.08)',
  lg: '0 8px 24px rgba(124, 58, 237, 0.10)',
  xl: '0 20px 40px rgba(124, 58, 237, 0.12)',
  soft: '0 4px 16px rgba(124, 58, 237, 0.08)',
  elevated: '0 20px 40px rgba(124, 58, 237, 0.12)',
} as const

export const typography = {
  fontFamily: {
    primary: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    metrics: "'Manrope', 'Inter', sans-serif",
  },
  fontSize: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '28px',
    '4xl': '36px',
  },
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  lineHeight: {
    tight: '1.2',
    normal: '1.5',
    relaxed: '1.6',
  },
} as const

export const transitions = {
  fast: '150ms ease',
  normal: '200ms ease',
  slow: '300ms ease',
  bounce: '200ms cubic-bezier(0.68, -0.55, 0.265, 1.55)',
} as const

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const

// Helper functions
export const getSpacing = (multiplier: number): string => {
  const base = 4 // 4px base unit
  return `${base * multiplier}px`
}

export const rgba = (hex: string, alpha: number): string => {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

