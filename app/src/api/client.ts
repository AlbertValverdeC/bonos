const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Projects
  listProjects: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : ''
    return request<any[]>(`/projects${qs}`)
  },
  getProject: (id: number) => request<any>(`/projects/${id}`),
  createProject: (data: { topic: string; channel_id?: number }) =>
    request<any>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id: number, data: any) =>
    request<any>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProject: (id: number) =>
    request<any>(`/projects/${id}`, { method: 'DELETE' }),

  // Pipeline
  generateScript: (id: number, data?: { duration_minutes?: number; extra_instructions?: string }) =>
    request<any>(`/projects/${id}/generate-script`, { method: 'POST', body: JSON.stringify(data || {}) }),
  approveScript: (id: number) =>
    request<any>(`/projects/${id}/approve-script`, { method: 'PUT' }),
  updateScript: (id: number, data: any) =>
    request<any>(`/projects/${id}/script`, { method: 'PUT', body: JSON.stringify(data) }),
  generateVoiceover: (id: number) =>
    request<any>(`/projects/${id}/generate-voiceover`, { method: 'POST', body: '{}' }),
  searchFootage: (id: number) =>
    request<any>(`/projects/${id}/search-footage`, { method: 'POST', body: '{}' }),
  assembleVideo: (id: number) =>
    request<any>(`/projects/${id}/assemble-video`, { method: 'POST', body: '{}' }),
  generateThumbnail: (id: number) =>
    request<any>(`/projects/${id}/generate-thumbnail`, { method: 'POST', body: '{}' }),
  uploadYoutube: (id: number, privacy?: string) =>
    request<any>(`/projects/${id}/upload-youtube`, { method: 'POST', body: JSON.stringify({ privacy: privacy || 'private' }) }),
  runPipeline: (id: number) =>
    request<any>(`/projects/${id}/run-pipeline`, { method: 'POST', body: '{}' }),

  // Channels
  listChannels: () => request<any[]>('/channels'),
  createChannel: (data: any) =>
    request<any>('/channels', { method: 'POST', body: JSON.stringify(data) }),
  updateChannel: (id: number, data: any) =>
    request<any>(`/channels/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Settings
  getKeys: () => request<any>('/settings/keys'),
  testKeys: () => request<any>('/settings/keys/test', { method: 'POST', body: '{}' }),
  getVoices: () => request<any>('/settings/voices'),
}
