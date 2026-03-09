import { useState } from 'react'
import type { ScriptSection } from '../types'

interface Props {
  sections: ScriptSection[]
  approved: boolean
  onApprove: () => void
  onSave: (sections: ScriptSection[]) => void
}

export default function ScriptEditor({ sections, approved, onApprove, onSave }: Props) {
  const [editing, setEditing] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const [editVisual, setEditVisual] = useState('')

  const totalDuration = sections.reduce((acc, s) => acc + (s.duration_estimate || 0), 0)
  const totalWords = sections.reduce((acc, s) => acc + s.narration_text.split(/\s+/).length, 0)

  function startEdit(section: ScriptSection) {
    setEditing(section.id)
    setEditText(section.narration_text)
    setEditVisual(section.visual_instructions)
  }

  function saveEdit(section: ScriptSection) {
    const updated = sections.map(s =>
      s.id === section.id
        ? { ...s, narration_text: editText, visual_instructions: editVisual }
        : s
    )
    onSave(updated)
    setEditing(null)
  }

  const typeColors: Record<string, string> = {
    hook: 'border-red-500 bg-red-500/5',
    intro: 'border-blue-500 bg-blue-500/5',
    body: 'border-gray-600 bg-gray-800/30',
    transition: 'border-purple-500 bg-purple-500/5',
    cta: 'border-green-500 bg-green-500/5',
    outro: 'border-yellow-500 bg-yellow-500/5',
  }

  const typeLabels: Record<string, string> = {
    hook: 'HOOK',
    intro: 'INTRO',
    body: 'CUERPO',
    transition: 'TRANSICIÓN',
    cta: 'CTA',
    outro: 'OUTRO',
  }

  return (
    <div>
      {/* Stats bar */}
      <div className="flex items-center justify-between mb-4 text-sm text-gray-400">
        <div className="flex gap-4">
          <span>{sections.length} secciones</span>
          <span>~{Math.round(totalDuration / 60)} min</span>
          <span>{totalWords.toLocaleString()} palabras</span>
        </div>
        <div className="flex gap-2">
          {!approved && (
            <button
              onClick={onApprove}
              className="px-4 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded text-sm font-medium transition-colors"
            >
              Aprobar Guion
            </button>
          )}
          {approved && (
            <span className="px-3 py-1.5 bg-green-600/20 text-green-400 rounded text-sm">
              Aprobado
            </span>
          )}
        </div>
      </div>

      {/* Sections */}
      <div className="space-y-3">
        {sections.map((section) => (
          <div
            key={section.id}
            className={`border-l-2 rounded-r-lg p-4 ${typeColors[section.section_type] || typeColors.body}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-gray-400 uppercase">
                  {typeLabels[section.section_type] || section.section_type}
                </span>
                <span className="text-xs text-gray-500">
                  ~{Math.round(section.duration_estimate)}s
                </span>
              </div>
              {editing !== section.id && (
                <button
                  onClick={() => startEdit(section)}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  Editar
                </button>
              )}
            </div>

            {editing === section.id ? (
              <div className="space-y-2">
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Narración</label>
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-gray-200 resize-y min-h-[80px]"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Instrucciones visuales</label>
                  <textarea
                    value={editVisual}
                    onChange={(e) => setEditVisual(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-gray-400 italic resize-y min-h-[40px]"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => saveEdit(section)}
                    className="px-3 py-1 bg-blue-600 text-white text-xs rounded"
                  >
                    Guardar
                  </button>
                  <button
                    onClick={() => setEditing(null)}
                    className="px-3 py-1 bg-gray-700 text-gray-300 text-xs rounded"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                  {section.narration_text}
                </p>
                {section.visual_instructions && (
                  <p className="text-xs text-gray-500 italic mt-2 border-t border-gray-800 pt-2">
                    🎥 {section.visual_instructions}
                  </p>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
