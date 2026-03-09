import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Project } from '../types'

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const data = await api.listProjects()
      setProjects(data)
    } catch (e) {
      console.error('Failed to load projects:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { projects, loading, refresh }
}

export function useProject(id: number | null) {
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await api.getProject(id)
      setProject(data)
    } catch (e) {
      console.error('Failed to load project:', e)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { refresh() }, [refresh])

  return { project, loading, refresh }
}
