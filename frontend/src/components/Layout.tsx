import { Link, Outlet } from 'react-router-dom'

import { ApiStatusBadge } from './ApiStatusBadge'

export const DISCLAIMER =
  'Prototipo de investigación. No es un dispositivo médico ni sustituye el diagnóstico de un especialista.'

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            MLOpérculo
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/" className="hover:underline">
              Estudios
            </Link>
            <Link to="/studies/new" className="hover:underline">
              Nuevo estudio
            </Link>
            <ApiStatusBadge />
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <p className="mx-auto max-w-6xl px-4 py-3 text-center text-xs text-slate-600">
          {DISCLAIMER}
        </p>
      </footer>
    </div>
  )
}
