import { ButtonHTMLAttributes, ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  children: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  style,
  children,
  ...props
}: ButtonProps) {
  const baseStyles: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: '600',
    borderRadius: '8px',
    transition: 'all 0.2s ease',
    border: 'none',
    cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
    opacity: disabled || isLoading ? 0.5 : 1
  }
  
  const variantStyles: Record<string, React.CSSProperties> = {
    primary: {
      background: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
      color: 'white'
    },
    secondary: {
      background: 'white',
      color: '#7C3AED',
      border: '2px solid #E5E7EB'
    },
    ghost: {
      background: 'transparent',
      color: '#7C3AED'
    },
    danger: {
      background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
      color: 'white'
    }
  }
  
  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: {
      fontSize: '14px',
      padding: '6px 12px',
      gap: '6px'
    },
    md: {
      fontSize: '16px',
      padding: '10px 20px',
      gap: '8px'
    },
    lg: {
      fontSize: '18px',
      padding: '12px 24px',
      gap: '10px'
    }
  }
  
  const hoverStyles = !disabled && !isLoading ? {
    onMouseEnter: (e: React.MouseEvent<HTMLButtonElement>) => {
      if (variant === 'primary' || variant === 'danger') {
        e.currentTarget.style.transform = 'translateY(-1px)'
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)'
      } else if (variant === 'secondary') {
        e.currentTarget.style.borderColor = '#7C3AED'
        e.currentTarget.style.background = '#F5F3FF'
      } else if (variant === 'ghost') {
        e.currentTarget.style.background = '#F5F3FF'
      }
    },
    onMouseLeave: (e: React.MouseEvent<HTMLButtonElement>) => {
      e.currentTarget.style.transform = 'translateY(0)'
      e.currentTarget.style.boxShadow = ''
      if (variant === 'secondary') {
        e.currentTarget.style.borderColor = '#E5E7EB'
        e.currentTarget.style.background = 'white'
      } else if (variant === 'ghost') {
        e.currentTarget.style.background = 'transparent'
      }
    }
  } : {}
  
  return (
    <button
      style={{
        ...baseStyles,
        ...variantStyles[variant],
        ...sizeStyles[size],
        ...style
      }}
      disabled={disabled || isLoading}
      {...hoverStyles}
      {...props}
    >
      {isLoading ? (
        <Loader2 
          size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16} 
          style={{ animation: 'spin 0.8s linear infinite' }}
        />
      ) : leftIcon}
      {children}
      {!isLoading && rightIcon}
    </button>
  )
}
