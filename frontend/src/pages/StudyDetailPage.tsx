import { useParams } from 'react-router-dom'

export function StudyDetailPage() {
  const { id } = useParams()

  return (
    <section>
      <h1 className="text-2xl font-semibold">Estudio {id}</h1>
      <p className="mt-2 text-slate-600">
        El detalle del estudio se implementará en los issues de la etapa 2.
      </p>
    </section>
  )
}
