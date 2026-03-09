import { useCallback, useState } from 'react'
import { api } from '../api/client'
import type { Project, ScriptSection } from '../types'
import { STATUS_LABELS } from '../types'
import PipelineSteps from './PipelineSteps'
import ScriptEditor from './ScriptEditor'

interface Props {
  project: Project
  onRefresh: () => void
}

export default function ProjectDetail({ project, onRefresh }: Props) {
  const [loading, setLoading] = useState('')
  const [duration, setDuration] = useState(15)

  const action = useCallback(async (label: string, fn: () => Promise<any>) => {
    setLoading(label)
    try {
      await fn()
      // Wait a moment for the backend to update
      setTimeout(onRefresh, 1000)
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    } finally {
      setLoading('')
    }
  }, [onRefresh])

  const handleApprove = () => action('Aprobando...', () => api.approveScript(project.id))

  const handleSaveSections = (sections: ScriptSection[]) => {
    action('Guardando...', () => api.updateScript(project.id, { sections }))
  }

  const handleRunPipeline = () => action('Ejecutando...', () => api.runPipeline(project.id))

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white mb-1">
          {project.title || project.topic}
        </h2>
        <p className="text-gray-400 text-sm">{project.topic}</p>
        {project.error_message && (
          <div className="mt-2 p-3 bg-red-900/30 border border-red-800 rounded text-red-300 text-sm">
            {project.error_message}
          </div>
        )}
      </div>

      {/* Pipeline steps */}
      <div className="mb-6">
        <PipelineSteps project={project} />
      </div>

      {/* Action buttons based on status */}
      <div className="mb-6 flex flex-wrap gap-3">
        {project.status === 'idea' && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-400">Duración:</label>
              <select
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white"
              >
                <option value={5}>5 min</option>
                <option value={10}>10 min</option>
                <option value={15}>15 min</option>
                <option value={20}>20 min</option>
                <option value={30}>30 min</option>
              </select>
            </div>
            <button
              onClick={() => action('Generando guion...', () => api.generateScript(project.id, { duration_minutes: duration }))}
              disabled={!!loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {loading === 'Generando guion...' ? '⏳ Generando...' : '📝 Generar Guion'}
            </button>
          </div>
        )}

        {project.status === 'script_review' && project.script_approved && (
          <button
            onClick={handleRunPipeline}
            disabled={!!loading}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {loading === 'Ejecutando...' ? '⏳ Ejecutando pipeline...' : '🚀 Ejecutar Pipeline Completo'}
          </button>
        )}

        {project.status === 'script_review' && project.script_approved && (
          <>
            <button
              onClick={() => action('Generando locución...', () => api.generateVoiceover(project.id))}
              disabled={!!loading}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              🎙 Solo Locución
            </button>
          </>
        )}

        {project.status === 'ready_to_upload' && (
          <button
            onClick={() => action('Subiendo...', () => api.uploadYoutube(project.id, 'private'))}
            disabled={!!loading}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            📤 Subir a YouTube (Privado)
          </button>
        )}

        {project.status === 'error' && (
          <button
            onClick={() => action('Reintentando...', () => api.runPipeline(project.id))}
            disabled={!!loading}
            className="px-4 py-2 bg-orange-600 hover:bg-orange-500 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            🔄 Reintentar
          </button>
        )}

        {project.status === 'published' && project.youtube_url && (
          <a
            href={project.youtube_url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2"
          >
            ▶ Ver en YouTube
          </a>
        )}
      </div>

      {/* Content sections based on status */}
      {project.sections && project.sections.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">Guion</h3>
          <ScriptEditor
            sections={project.sections}
            approved={project.script_approved}
            onApprove={handleApprove}
            onSave={handleSaveSections}
          />
        </div>
      )}

      {/* Audio player */}
      {project.audio_filename && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">Locución</h3>
          <div className="bg-gray-900 rounded-lg p-4">
            <audio
              controls
              src={`/api/settings/media/audio/${project.audio_filename}`}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-2">
              Duración estimada: {Math.round(project.audio_duration / 60)} min
            </p>
          </div>
        </div>
      )}

      {/* Thumbnail preview */}
      {project.thumbnail_filename && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">Miniatura</h3>
          <img
            src={`/api/settings/media/thumbnails/${project.thumbnail_filename}`}
            alt="Thumbnail"
            className="rounded-lg max-w-lg shadow-lg"
          />
        </div>
      )}

      {/* Video preview */}
      {project.video_filename && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">Vídeo Final</h3>
          <video
            controls
            src={`/api/settings/media/output/${project.video_filename}`}
            className="rounded-lg max-w-2xl w-full"
          />
        </div>
      )}

      {/* Footage gallery */}
      {project.footage_clips && project.footage_clips.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">
            Footage ({project.footage_clips.length} clips)
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {project.footage_clips.map((clip) => (
              <div
                key={clip.id}
                className={`rounded-lg border-2 p-2 ${
                  clip.selected ? 'border-green-500 bg-green-500/5' : 'border-gray-700 bg-gray-900'
                }`}
              >
                <p className="text-xs text-gray-400 truncate">{clip.search_query}</p>
                <p className="text-xs text-gray-500">{clip.source} | {Math.round(clip.duration)}s</p>
                {clip.selected && <span className="text-xs text-green-400">Seleccionado</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debug info */}
      <details className="mt-8">
        <summary className="text-xs text-gray-600 cursor-pointer">Debug info</summary>
        <pre className="text-xs text-gray-600 mt-2 overflow-auto">
          {JSON.stringify(project, null, 2)}
        </pre>
      </details>
    </div>
  )
}
