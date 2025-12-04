import React from 'react'

interface FakeCursorProps {
  x: number
  y: number
  visible: boolean
}

export function FakeCursor({ x, y, visible }: FakeCursorProps) {
  // Debug: log quando il cursore dovrebbe essere visibile
  React.useEffect(() => {
    if (visible) {
      console.log(`[FakeCursor] ✅ Cursore finto VISIBILE a (${x}, ${y})`)
    } else {
      console.log(`[FakeCursor] ❌ Cursore finto NASCOSTO`)
    }
  }, [visible, x, y])

  if (!visible) {
    console.log(`[FakeCursor] Render: visible=false, non renderizzo`)
    return null
  }
  
  console.log(`[FakeCursor] Render: visible=true, renderizzo a (${x}, ${y})`)

  return (
    <div
      style={{
        position: 'fixed',
        left: `${x}px`,
        top: `${y}px`,
        width: '16px',
        height: '16px',
        pointerEvents: 'none',
        zIndex: 999999,
        transform: 'translate(-2px, -2px)',
        transition: 'none', // No transition for smooth following
      }}
    >
      {/* Cursore freccia nera con bordo bianco */}
      <svg
        width="16"
        height="16"
        viewBox="0 0 16 16"
        style={{
          filter: 'drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3))',
        }}
      >
        <path
          d="M 0 0 L 12 0 L 12 4 L 16 4 L 8 16 L 6 12 L 0 12 Z"
          fill="#000000"
          stroke="#FFFFFF"
          strokeWidth="0.5"
        />
      </svg>
    </div>
  )
}

