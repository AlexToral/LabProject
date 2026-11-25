import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section>
      <h1 className="text-2xl font-semibold">Página no encontrada</h1>
      <Link to="/" className="mt-2 inline-block text-blue-700 hover:underline">
        Volver a la lista de estudios
      </Link>
    </section>
  )
}
