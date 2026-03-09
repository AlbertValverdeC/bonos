export interface Channel {
  id: number
  name: string
  niche: string
  language: string
  youtube_channel_id: string
  voice_id: string
  style_prompt: string
  thumbnail_style: string
  created_at: string
}

export interface ScriptSection {
  id: number
  project_id: number
  position: number
  section_type: string
  narration_text: string
  visual_instructions: string
  duration_estimate: number
}

export interface FootageClip {
  id: number
  project_id: number
  section_id: number | null
  source: string
  source_url: string
  local_filename: string
  duration: number
  search_query: string
  selected: boolean
}

export interface Project {
  id: number
  channel_id: number | null
  title: string
  topic: string
  status: string
  current_step: number
  script: string
  script_approved: boolean
  audio_filename: string
  audio_duration: number
  video_filename: string
  thumbnail_filename: string
  youtube_video_id: string
  youtube_url: string
  scheduled_at: string | null
  published_at: string | null
  error_message: string
  created_at: string
  updated_at: string
  sections?: ScriptSection[]
  footage_clips?: FootageClip[]
}

export interface PipelineEvent {
  type: string
  data: {
    project_id: number
    step: string
    result?: Record<string, unknown>
    error?: string
  }
  timestamp: string
}

export const PIPELINE_STEPS = [
  { key: 'idea', label: 'Idea', icon: '💡' },
  { key: 'scripting', label: 'Guion', icon: '📝' },
  { key: 'script_review', label: 'Revisión', icon: '👁' },
  { key: 'voiceover', label: 'Locución', icon: '🎙' },
  { key: 'footage', label: 'Footage', icon: '🎥' },
  { key: 'assembling', label: 'Montaje', icon: '🔧' },
  { key: 'thumbnail', label: 'Miniatura', icon: '🖼' },
  { key: 'ready_to_upload', label: 'Subida', icon: '📤' },
] as const

export const STATUS_LABELS: Record<string, string> = {
  idea: 'Idea',
  scripting: 'Generando guion...',
  script_review: 'Pendiente de revisión',
  voiceover: 'Generando locución...',
  footage: 'Buscando footage...',
  assembling: 'Montando vídeo...',
  thumbnail: 'Generando miniatura...',
  ready_to_upload: 'Listo para subir',
  uploading: 'Subiendo a YouTube...',
  published: 'Publicado',
  error: 'Error',
}
