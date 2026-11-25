import { useEffect, useState } from 'react'

import { getHealth } from '../services/api'
import type { ApiStatus } from '../types/api'

const POLL_INTERVAL_MS = 30_000
const REQUEST_TIMEOUT_MS = 5_000

const LABELS: Record<ApiStatus, string> = {
  checking: 'Comprobando API…',
  online: 'API disponible',
  offline: 'API no disponible',
}

const DOT_COLORS: Record<ApiStatus, string> = {
  checking: 'bg-slate-400',
  online: 'bg-emerald-500',
  offline: 'bg-red-500',
}

export function ApiStatusBadge() {
  const [status, setStatus] = useState<ApiStatus>('checking')

  useEffect(() => {
    let controller: AbortController | undefined

    const check = async () => {
      controller?.abort()
      const current = new AbortController()
      controller = current
      const timeout = window.setTimeout(() => current.abort(), REQUEST_TIMEOUT_MS)
      try {
        const health = await getHealth(current.signal)
        setStatus(health.status === 'ok' ? 'online' : 'offline')
      } catch {
        // Ignorar el error si la petición se canceló al desmontar el componente.
        if (controller === current) setStatus('offline')
      } finally {
        window.clearTimeout(timeout)
      }
    }

    void check()
    const interval = window.setInterval(() => void check(), POLL_INTERVAL_MS)
    return () => {
      window.clearInterval(interval)
      const pending = controller
      controller = undefined
      pending?.abort()
    }
  }, [])

  return (
    <span
      role="status"
      aria-live="polite"
      className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-sm text-slate-700"
    >
      <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${DOT_COLORS[status]}`} />
      {LABELS[status]}
    </span>
  )
}
