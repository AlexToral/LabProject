import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import { Layout } from './components/Layout'
import { NewStudyPage } from './pages/NewStudyPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { StudiesPage } from './pages/StudiesPage'
import { StudyDetailPage } from './pages/StudyDetailPage'

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <StudiesPage /> },
      { path: '/studies/new', element: <NewStudyPage /> },
      { path: '/studies/:id', element: <StudyDetailPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
