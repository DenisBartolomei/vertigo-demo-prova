interface SkeletonProps {
  width?: string | number
  height?: string | number
  circle?: boolean
  count?: number
  style?: React.CSSProperties
}

export function Skeleton({
  width,
  height = '16px',
  circle = false,
  count = 1,
  style
}: SkeletonProps) {
  const skeletons = Array.from({ length: count }, (_, i) => i)
  
  const baseStyles: React.CSSProperties = {
    width,
    height,
    borderRadius: circle ? '50%' : '8px',
    background: 'linear-gradient(90deg, #F9FAFB 0%, rgba(124, 58, 237, 0.05) 50%, #F9FAFB 100%)',
    backgroundSize: '1000px 100%',
    animation: 'shimmer 1.5s infinite'
  }
  
  if (count === 1) {
    return (
      <div
        className="skeleton"
        style={{ ...baseStyles, ...style }}
      />
    )
  }
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {skeletons.map((key) => (
        <div
          key={key}
          className="skeleton"
          style={{ ...baseStyles, ...style }}
        />
      ))}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div style={{
      background: 'white',
      borderRadius: '12px',
      border: '1px solid #E5E7EB',
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <Skeleton circle width={48} height={48} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <Skeleton width="60%" height="20px" />
          <Skeleton width="40%" height="16px" />
        </div>
      </div>
      <Skeleton width="100%" height="12px" count={3} />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <Skeleton width="100%" height="48px" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} width="100%" height="56px" />
      ))}
    </div>
  )
}
