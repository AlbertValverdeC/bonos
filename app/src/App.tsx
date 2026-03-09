import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client'
import type { Channel, Project } from './types'
import { usePipeline } from './hooks/usePipeline'
import Layout from './components/Layout'
import ProjectList from './components/ProjectList'
import ProjectDetail from './components/ProjectDetail'
import NewProjectDialog from './components/NewProjectDialog'
import ResearchPage from './components/ResearchPage'

type Page = 'projects' | 'research'

export default function App() {
  const [page, setPage] = useState<Page>('research')
  const [projects, setProjects] = useState<Project[]>([])
  const [channels, setChannels] = useState<Channel[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [showNewDialog, setShowNewDialog] = useState(false)

  const loadProjects = useCallback(async () => {
    try {
      const data = await api.listProjects()
      setProjects(data)
    } catch (e) {
      console.error('Failed to load projects:', e)
    }
  }, [])

  const loadChannels = useCallback(async () => {
    try {
      const data = await api.listChannels()
      setChannels(data)
    } catch (e) {
      console.error('Failed to load channels:', e)
    }
  }, [])

  const loadProject = useCallback(async () => {
    if (!selectedId) {
      setSelectedProject(null)
      return
    }
    try {
      const data = await api.getProject(selectedId)
      setSelectedProject(data)
    } catch (e) {
      console.error('Failed to load project:', e)
    }
  }, [selectedId])

  useEffect(() => { loadProjects(); loadChannels() }, [loadProjects, loadChannels])
  useEffect(() => { loadProject() }, [loadProject])

  usePipeline((event) => {
    if (event.data.project_id === selectedId) {
      loadProject()
    }
    loadProjects()
  })

  function handleCreated(id: number) {
    setShowNewDialog(false)
    setSelectedId(id)
    setPage('projects')
    loadProjects()
  }

  async function handleCreateFromResearch(title: string, topic: string) {
    try {
      const project = await api.createProject({
        topic,
        channel_id: channels[0]?.id,
      })
      setSelectedId(project.id)
      setPage('projects')
      loadProjects()
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    }
  }

  return (
    <Layout
      sidebar={
        <div className="flex flex-col h-full">
          {/* Navigation tabs */}
          <div className="flex border-b border-gray-800">
            <button
              onClick={() => setPage('research')}
              className={`flex-1 py-3 text-xs font-medium transition-colors ${
                page === 'research'
                  ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-800/50'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              🔍 Investigación
            </button>
            <button
              onClick={() => setPage('projects')}
              className={`flex-1 py-3 text-xs font-medium transition-colors ${
                page === 'projects'
                  ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-800/50'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              🎬 Proyectos ({projects.length})
            </button>
          </div>

          {/* Sidebar content */}
          {page === 'projects' ? (
            <ProjectList
              projects={projects}
              selectedId={selectedId}
              onSelect={(id) => { setSelectedId(id); setPage('projects') }}
              onCreate={() => setShowNewDialog(true)}
            />
          ) : (
            <div className="p-4 text-sm text-gray-400">
              <p className="mb-3">Descubre los mejores nichos y genera ideas virales con IA.</p>
              <p className="text-xs text-gray-600">
                El análisis evalúa RPM, competencia, facilidad de producción y potencial de automatización.
              </p>

              {projects.length > 0 && (
                <div className="mt-6">
                  <p className="text-xs text-gray-500 mb-2 font-medium">Proyectos recientes:</p>
                  {projects.slice(0, 5).map(p => (
                    <button
                      key={p.id}
                      onClick={() => { setSelectedId(p.id); setPage('projects') }}
                      className="block w-full text-left text-xs text-gray-400 hover:text-white py-1 truncate"
                    >
                      {p.title || p.topic}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      }
    >
      {page === 'research' ? (
        <ResearchPage onCreateProject={handleCreateFromResearch} />
      ) : selectedProject ? (
        <ProjectDetail
          project={selectedProject}
          onRefresh={() => { loadProject(); loadProjects() }}
        />
      ) : (
        <div className="flex items-center justify-center h-full text-gray-600">
          <div className="text-center">
            <p className="text-6xl mb-4">🎬</p>
            <p className="text-lg">Selecciona un proyecto o crea uno nuevo</p>
            <button
              onClick={() => setShowNewDialog(true)}
              className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              + Nuevo Proyecto
            </button>
          </div>
        </div>
      )}

      {showNewDialog && (
        <NewProjectDialog
          channels={channels}
          onCreated={handleCreated}
          onClose={() => setShowNewDialog(false)}
        />
      )}
    </Layout>
  )
}
