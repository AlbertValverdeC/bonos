import { useState } from 'react'
import { api } from '../api/client'
import type { Channel } from '../types'

interface Props {
  channels: Channel[]
  onCreated: (id: number) => void
  onClose: () => void
}

export default function NewProjectDialog({ channels, onCreated, onClose }: Props) {
  const [topic, setTopic] = useState('')
  const [channelId, setChannelId] = useState<number | undefined>(channels[0]?.id)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!topic.trim()) return

    setLoading(true)
    try {
      const project = await api.createProject({
        topic: topic.trim(),
        channel_id: channelId,
      })
      onCreated(project.id)
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 rounded-xl p-6 w-full max-w-lg shadow-2xl" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-white mb-4">Nuevo Proyecto</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Tema del vídeo</label>
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder='Ej: "5 formas de ganar dinero con IA en 2026"'
              className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-white placeholder-gray-500 resize-y min-h-[80px]"
              autoFocus
            />
          </div>

          {channels.length > 0 && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">Canal</label>
              <select
                value={channelId}
                onChange={(e) => setChannelId(Number(e.target.value) || undefined)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white"
              >
                <option value="">Sin canal asignado</option>
                {channels.map(c => (
                  <option key={c.id} value={c.id}>{c.name} ({c.niche})</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={!topic.trim() || loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium"
            >
              {loading ? 'Creando...' : 'Crear Proyecto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
