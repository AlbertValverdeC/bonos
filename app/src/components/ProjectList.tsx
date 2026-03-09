import type { Project } from '../types'
import { STATUS_LABELS } from '../types'

interface Props {
  projects: Project[]
  selectedId: number | null
  onSelect: (id: number) => void
  onCreate: () => void
}

export default function ProjectList({ projects, selectedId, onSelect, onCreate }: Props) {
  const statusColor: Record<string, string> = {
    idea: 'bg-gray-600',
    scripting: 'bg-yellow-600 animate-pulse',
    script_review: 'bg-orange-500',
    voiceover: 'bg-yellow-600 animate-pulse',
    footage: 'bg-yellow-600 animate-pulse',
    assembling: 'bg-yellow-600 animate-pulse',
    thumbnail: 'bg-yellow-600 animate-pulse',
    ready_to_upload: 'bg-blue-500',
    uploading: 'bg-blue-500 animate-pulse',
    published: 'bg-green-500',
    error: 'bg-red-500',
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3">
        <button
          onClick={onCreate}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + Nuevo Proyecto
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {projects.length === 0 ? (
          <p className="text-gray-500 text-sm text-center p-4">
            No hay proyectos. Crea el primero.
          </p>
        ) : (
          projects.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelect(p.id)}
              className={`
                w-full text-left p-3 border-b border-gray-800 hover:bg-gray-800/50 transition-colors
                ${selectedId === p.id ? 'bg-gray-800 border-l-2 border-l-blue-500' : ''}
              `}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-200 truncate">
                    {p.title || p.topic}
                  </p>
                  <p className="text-xs text-gray-500 mt-1 truncate">{p.topic}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className={`w-2 h-2 rounded-full ${statusColor[p.status] || 'bg-gray-600'}`} />
                  <span className="text-xs text-gray-400">
                    {STATUS_LABELS[p.status] || p.status}
                  </span>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
