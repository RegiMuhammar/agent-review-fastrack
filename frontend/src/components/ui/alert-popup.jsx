import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'

function AlertPopup({
  open,
  title,
  description,
  variant = 'info',
  confirmLabel = 'OK',
  cancelLabel,
  onConfirm,
  onCancel,
  destructive = false,
}) {
  const resolvedVariant = destructive ? 'error' : variant
  const [shouldRender, setShouldRender] = useState(open)
  const [isVisible, setIsVisible] = useState(open)

  useEffect(() => {
    if (open) {
      setShouldRender(true)

      const frame = window.requestAnimationFrame(() => {
        setIsVisible(true)
      })

      return () => window.cancelAnimationFrame(frame)
    }

    setIsVisible(false)

    const timer = window.setTimeout(() => {
      setShouldRender(false)
    }, 220)

    return () => window.clearTimeout(timer)
  }, [open])

  useEffect(() => {
    if (!open) {
      return
    }

    const onKeyDown = (event) => {
      if (event.key !== 'Escape') {
        return
      }

      if (onCancel) {
        onCancel()
        return
      }

      if (onConfirm) {
        onConfirm()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onCancel, onConfirm])

  const variantStyleMap = {
    success: 'border-emerald-200 bg-emerald-50 text-emerald-600',
    warning: 'border-amber-200 bg-amber-50 text-amber-600',
    error: 'border-red-200 bg-red-50 text-red-600',
    info: 'border-[#5E74C9]/25 bg-[#5E74C9]/10 text-[#2E3F86]',
  }

  const variantClassName = variantStyleMap[resolvedVariant] || variantStyleMap.info

  const variantIconMap = {
    success: CheckCircle2,
    warning: AlertTriangle,
    error: XCircle,
    info: Info,
  }

  const VariantIcon = variantIconMap[resolvedVariant] || variantIconMap.info

  if (!shouldRender) {
    return null
  }

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-[2px] transition-all duration-200 ${
        isVisible ? 'bg-[#0b122833] opacity-100' : 'bg-[#0b122800] opacity-0'
      }`}
      onClick={() => {
        if (onCancel) {
          onCancel()
        }
      }}
    >
      <div
        className={`w-full max-w-md rounded-2xl border border-[#5E74C9]/18 bg-white p-5 shadow-[0_25px_80px_rgba(46,63,134,0.25)] transition-all duration-300 ${
          isVisible
            ? 'translate-y-0 scale-100 opacity-100'
            : 'translate-y-2 scale-95 opacity-0'
        }`}
        style={
          isVisible && resolvedVariant === 'error'
            ? { animation: 'alert-popup-shake 360ms ease-in-out 1' }
            : undefined
        }
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-3 flex justify-center">
          <div
            className={`flex h-14 w-14 items-center justify-center rounded-full border transition-all duration-300 ${variantClassName} ${
              isVisible ? 'scale-100' : 'scale-75'
            }`}
          >
            <VariantIcon className="size-7" />
          </div>
        </div>

        <h3 className="text-lg font-semibold text-[#2E3F86]">{title}</h3>
        <p className="mt-2 text-sm text-[#5f73b1]">{description}</p>

        <div className="mt-5 flex justify-end gap-2">
          {cancelLabel ? (
            <Button type="button" variant="outline" onClick={onCancel}>
              {cancelLabel}
            </Button>
          ) : null}
          <Button
            type="button"
            className={destructive ? 'bg-red-600 text-white hover:bg-red-700' : undefined}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>

      <style>{`
        @keyframes alert-popup-shake {
          0% { transform: translateX(0); }
          20% { transform: translateX(-6px); }
          40% { transform: translateX(6px); }
          60% { transform: translateX(-4px); }
          80% { transform: translateX(4px); }
          100% { transform: translateX(0); }
        }
      `}</style>
    </div>
  )
}

export default AlertPopup
