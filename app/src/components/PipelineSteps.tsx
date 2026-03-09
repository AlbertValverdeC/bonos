import { PIPELINE_STEPS } from '../types'
import type { Project } from '../types'

interface Props {
  project: Project
}

export default function PipelineSteps({ project }: Props) {
  const statusIndex = PIPELINE_STEPS.findIndex(s => s.key === project.status)

  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-2">
      {PIPELINE_STEPS.map((step, i) => {
        const isActive = step.key === project.status
        const isComplete = i < statusIndex || project.status === 'published'
        const isError = project.status === 'error' && i === statusIndex

        return (
          <div key={step.key} className="flex items-center">
            {i > 0 && (
              <div className={`w-6 h-0.5 ${isComplete ? 'bg-green-500' : 'bg-gray-700'}`} />
            )}
            <div
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap
                ${isActive ? 'bg-blue-600 text-white ring-2 ring-blue-400/50' : ''}
                ${isComplete ? 'bg-green-600/20 text-green-400' : ''}
                ${isError ? 'bg-red-600/20 text-red-400 ring-2 ring-red-400/50' : ''}
                ${!isActive && !isComplete && !isError ? 'bg-gray-800 text-gray-500' : ''}
              `}
            >
              <span>{step.icon}</span>
              <span>{step.label}</span>
            </div>
          </div>
        )
      })}
      {project.status === 'published' && (
        <div className="flex items-center">
          <div className="w-6 h-0.5 bg-green-500" />
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-green-600/20 text-green-400">
            <span>✅</span>
            <span>Publicado</span>
          </div>
        </div>
      )}
    </div>
  )
}
