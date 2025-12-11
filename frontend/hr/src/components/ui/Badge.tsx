import { ReactNode } from 'react'

interface BadgeProps {
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'purple'
  size?: 'sm' | 'md' | 'lg'
  dot?: boolean
  children: ReactNode
  style?: React.CSSProperties
}

export function Badge({
  variant = 'neutral',
  size = 'md',
  dot = false,
  children,
  style
}: BadgeProps) {
  const variantStyles: Record<string, React.CSSProperties> = {
    success: {
      background: '#D1FAE5',
      color: '#065F46',
      borderColor: 'rgba(16, 185, 129, 0.2)'
    },
    warning: {
      background: '#FEF3C7',
      color: '#92400E',
      borderColor: 'rgba(245, 158, 11, 0.2)'
    },
    error: {
      background: '#FEE2E2',
      color: '#991B1B',
      borderColor: 'rgba(239, 68, 68, 0.2)'
    },
    info: {
      background: '#DBEAFE',
      color: '#1E40AF',
      borderColor: 'rgba(59, 130, 246, 0.2)'
    },
    neutral: {
      background: '#F3F4F6',
      color: '#374151',
      borderColor: 'rgba(156, 163, 175, 0.2)'
    },
    purple: {
      background: '#F5F3FF',
      color: '#7C3AED',
      borderColor: 'rgba(124, 58, 237, 0.2)'
    }
  }
  
  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: {
      fontSize: '12px',
      padding: '2px 8px'
    },
    md: {
      fontSize: '14px',
      padding: '4px 10px'
    },
    lg: {
      fontSize: '16px',
      padding: '6px 12px'
    }
  }
  
  const dotColors: Record<string, string> = {
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
    neutral: '#6B7280',
    purple: '#7C3AED'
  }
  
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        borderRadius: '9999px',
        border: '1px solid',
        fontWeight: '500',
        ...variantStyles[variant],
        ...sizeStyles[size],
        ...style
      }}
    >
      {dot && (
        <span style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: dotColors[variant],
          flexShrink: 0
        }} />
      )}
      {children}
    </span>
  )
}
