import { InputHTMLAttributes, ReactNode, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  fullWidth?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      style,
      disabled,
      ...props
    },
    ref
  ) => {
    const hasError = !!error
    
    return (
      <div style={{ width: fullWidth ? '100%' : 'auto' }}>
        {label && (
          <label style={{
            display: 'block',
            fontSize: '14px',
            fontWeight: '500',
            color: '#1F2937',
            marginBottom: '6px'
          }}>
            {label}
          </label>
        )}
        <div style={{ position: 'relative' }}>
          {leftIcon && (
            <div style={{
              position: 'absolute',
              left: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#6B7280',
              pointerEvents: 'none'
            }}>
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            style={{
              width: '100%',
              padding: '10px 16px',
              paddingLeft: leftIcon ? '40px' : '16px',
              paddingRight: rightIcon ? '40px' : '16px',
              border: `2px solid ${hasError ? '#FCA5A5' : '#E5E7EB'}`,
              borderRadius: '8px',
              fontSize: '15px',
              outline: 'none',
              transition: 'all 0.2s ease',
              background: disabled ? '#F9FAFB' : 'white',
              cursor: disabled ? 'not-allowed' : 'text',
              ...(hasError ? {
                borderColor: '#FCA5A5'
              } : {}),
              ...style
            }}
            onFocus={(e) => {
              if (!hasError) {
                e.currentTarget.style.borderColor = '#7C3AED'
                e.currentTarget.style.boxShadow = '0 0 0 3px rgba(124, 58, 237, 0.1)'
              } else {
                e.currentTarget.style.borderColor = '#EF4444'
                e.currentTarget.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)'
              }
            }}
            onBlur={(e) => {
              e.currentTarget.style.boxShadow = ''
              if (!hasError) {
                e.currentTarget.style.borderColor = '#E5E7EB'
              }
            }}
            disabled={disabled}
            {...props}
          />
          {rightIcon && (
            <div style={{
              position: 'absolute',
              right: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#6B7280',
              display: 'flex',
              alignItems: 'center'
            }}>
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="slide-down" style={{
            marginTop: '6px',
            fontSize: '14px',
            color: '#DC2626',
            marginBottom: 0
          }}>
            {error}
          </p>
        )}
        {helperText && !error && (
          <p style={{
            marginTop: '6px',
            fontSize: '14px',
            color: '#6B7280',
            marginBottom: 0
          }}>
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
