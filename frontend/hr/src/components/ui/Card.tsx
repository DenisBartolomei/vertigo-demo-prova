import { HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevation?: 'sm' | 'md' | 'lg' | 'xl'
  hoverable?: boolean
  clickable?: boolean
  children: ReactNode
}

export function Card({
  elevation = 'sm',
  hoverable = false,
  clickable = false,
  style,
  children,
  ...props
}: CardProps) {
  const shadowMap: Record<string, string> = {
    sm: '0 2px 8px rgba(124, 58, 237, 0.06)',
    md: '0 4px 16px rgba(124, 58, 237, 0.08)',
    lg: '0 8px 24px rgba(124, 58, 237, 0.10)',
    xl: '0 20px 40px rgba(124, 58, 237, 0.12)'
  }
  
  const baseStyles: React.CSSProperties = {
    background: 'white',
    borderRadius: '12px',
    border: '1px solid #E5E7EB',
    transition: 'all 0.2s ease',
    boxShadow: shadowMap[elevation]
  }
  
  const hoverStyles = hoverable ? {
    onMouseEnter: (e: React.MouseEvent<HTMLDivElement>) => {
      e.currentTarget.style.transform = 'translateY(-4px)'
      e.currentTarget.style.boxShadow = '0 8px 24px rgba(124, 58, 237, 0.15)'
    },
    onMouseLeave: (e: React.MouseEvent<HTMLDivElement>) => {
      e.currentTarget.style.transform = 'translateY(0)'
      e.currentTarget.style.boxShadow = shadowMap[elevation]
    }
  } : {}
  
  const clickableStyles: React.CSSProperties = clickable ? {
    cursor: 'pointer'
  } : {}
  
  return (
    <div
      style={{
        ...baseStyles,
        ...clickableStyles,
        ...style
      }}
      {...hoverStyles}
      {...props}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: ReactNode
  style?: React.CSSProperties
}

export function CardHeader({ children, style }: CardHeaderProps) {
  return (
    <div style={{
      padding: '16px 24px',
      borderBottom: '1px solid #E5E7EB',
      ...style
    }}>
      {children}
    </div>
  )
}

interface CardBodyProps {
  children: ReactNode
  style?: React.CSSProperties
}

export function CardBody({ children, style }: CardBodyProps) {
  return (
    <div style={{
      padding: '16px 24px',
      ...style
    }}>
      {children}
    </div>
  )
}

interface CardFooterProps {
  children: ReactNode
  style?: React.CSSProperties
}

export function CardFooter({ children, style }: CardFooterProps) {
  return (
    <div style={{
      padding: '16px 24px',
      borderTop: '1px solid #E5E7EB',
      ...style
    }}>
      {children}
    </div>
  )
}
