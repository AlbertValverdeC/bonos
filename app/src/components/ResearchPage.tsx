import { useState, useCallback } from 'react'

interface NicheResult {
  rank: number
  name: string
  rpm_estimate: string
  competition: number
  production_ease: number
  ai_automation: number
  content_format: string
  target_audience: string
  reference_channels: string[]
  opportunity_window: string
  score: number
  rationale: string
  video_ideas?: VideoIdea[]
}

interface VideoIdea {
  rank: number
  title: string
  duration_minutes: number
  traffic_source: string
  content_type: string
  hook: string
  keywords: string[]
  rationale: string
  viral_score: number
  english_inspiration: string
}

interface DataSources {
  youtube_api: boolean
  google_trends: boolean
  openai: boolean
  message: string
}

interface Props {
  onCreateProject: (title: string, topic: string) => void
}

export default function ResearchPage({ onCreateProject }: Props) {
  const [status, setStatus] = useState<'idle' | 'discovering' | 'scanning' | 'ideas' | 'done' | 'error'>('idle')
  const [scanProgress, setScanProgress] = useState('')
  const [niches, setNiches] = useState<NicheResult[]>([])
  const [summary, setSummary] = useState('')
  const [dataSource, setDataSource] = useState('')
  const [selectedNiche, setSelectedNiche] = useState<NicheResult | null>(null)
  const [ideas, setIdeas] = useState<VideoIdea[]>([])
  const [error, setError] = useState('')
  const [sources, setSources] = useState<DataSources | null>(null)

  // Preferences
  const [language, setLanguage] = useState('es')
  const [interests, setInterests] = useState('')
  const [avoid, setAvoid] = useState('')

  // Check available data sources on mount
  useState(() => {
    fetch('/api/research/status-check')
      .then(r => r.json())
      .then(setSources)
      .catch(() => {})
  })

  const discoverNiches = useCallback(async () => {
    setStatus('discovering')
    setError('')
    try {
      const res = await fetch('/api/research/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: {
            language,
            interests: interests || undefined,
            avoid: avoid || undefined,
          },
        }),
      })
      await res.json()

      // Poll for results
      while (true) {
        await new Promise(r => setTimeout(r, 2000))
        const statusRes = await fetch('/api/research/status/latest')
        const statusData = await statusRes.json()

        if (statusData.status === 'completed') {
          const resultRes = await fetch('/api/research/results/latest')
          const resultData = await resultRes.json()
          setNiches(resultData.data?.niches || [])
          setSummary(resultData.data?.analysis_summary || '')
          setDataSource(resultData.data?.data_source || '')
          setStatus('done')
          break
        } else if (statusData.status === 'error') {
          const resultRes = await fetch('/api/research/results/latest')
          const resultData = await resultRes.json()
          setError(resultData.data?.error || 'Error desconocido')
          setStatus('error')
          break
        }
      }
    } catch (e: any) {
      setError(e.message)
      setStatus('error')
    }
  }, [language, interests, avoid])

  const deepScan = useCallback(async () => {
    setStatus('scanning')
    setError('')
    setScanProgress('Iniciando escaneo masivo...')
    try {
      await fetch('/api/research/deep-scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })

      // Poll for results
      while (true) {
        await new Promise(r => setTimeout(r, 3000))
        const statusRes = await fetch('/api/research/status/deep_scan')
        const statusData = await statusRes.json()

        if (statusData.status === 'running') {
          // Check progress
          const progressRes = await fetch('/api/research/results/deep_scan')
          const progressData = await progressRes.json()
          if (progressData.data?.progress) {
            setScanProgress(progressData.data.progress)
          }
        } else if (statusData.status === 'completed') {
          const resultRes = await fetch('/api/research/results/deep_scan')
          const resultData = await resultRes.json()
          const analysis = resultData.data?.ai_analysis || {}
          setNiches(analysis.niches || [])
          setSummary(analysis.analysis_summary || '')
          setIdeas(analysis.video_ideas || [])
          setDataSource('deep_scan_real_data')

          // Store scan metadata for display
          const meta = resultData.data?.scan_metadata
          if (meta) {
            setSummary(prev =>
              `📊 Scan: ${meta.keywords_searched} keywords → ${meta.total_videos_found} vídeos → ${meta.unique_channels_analyzed} canales → ${meta.outliers_found} outliers reales\n\n${prev}`
            )
          }

          setStatus('done')
          break
        } else if (statusData.status === 'error') {
          const resultRes = await fetch('/api/research/results/deep_scan')
          const resultData = await resultRes.json()
          setError(resultData.data?.error || 'Error desconocido')
          setStatus('error')
          break
        }
      }
    } catch (e: any) {
      setError(e.message)
      setStatus('error')
    }
  }, [])

  const loadIdeas = useCallback(async (niche: NicheResult) => {
    setSelectedNiche(niche)

    // If ideas already loaded (from full research), use them
    if (niche.video_ideas && niche.video_ideas.length > 0) {
      setIdeas(niche.video_ideas)
      return
    }

    setStatus('ideas')
    try {
      const res = await fetch('/api/research/ideas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ niche: niche.name, count: 15 }),
      })
      await res.json()

      const researchId = `ideas_${niche.name}`
      while (true) {
        await new Promise(r => setTimeout(r, 2000))
        const statusRes = await fetch(`/api/research/status/${encodeURIComponent(researchId)}`)
        const statusData = await statusRes.json()

        if (statusData.status === 'completed') {
          const resultRes = await fetch(`/api/research/results/${encodeURIComponent(researchId)}`)
          const resultData = await resultRes.json()
          setIdeas(resultData.data?.ideas || [])
          setStatus('done')
          break
        } else if (statusData.status === 'error') {
          setStatus('done')
          break
        }
      }
    } catch (e: any) {
      setStatus('done')
    }
  }, [])

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h2 className="text-2xl font-bold text-white mb-2">Investigación de Mercado</h2>
      <p className="text-gray-400 text-sm mb-4">
        Análisis automático de nichos y generación de ideas virales basado en datos reales.
      </p>

      {/* Data sources indicator */}
      {sources && (
        <div className="flex gap-3 mb-6 text-xs">
          <span className={`px-2 py-1 rounded ${sources.youtube_api ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
            {sources.youtube_api ? '✓' : '✗'} YouTube Data API
          </span>
          <span className={`px-2 py-1 rounded ${sources.google_trends ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
            {sources.google_trends ? '✓' : '✗'} Google Trends
          </span>
          <span className="px-2 py-1 rounded bg-green-900/30 text-green-400">
            ✓ OpenAI (análisis)
          </span>
          {!sources.youtube_api && (
            <span className="px-2 py-1 rounded bg-yellow-900/30 text-yellow-400">
              Configura YOUTUBE_API_KEY en .env para datos reales
            </span>
          )}
        </div>
      )}

      {/* Preferences */}
      {status === 'idle' && (
        <div className="bg-gray-900 rounded-xl p-6 mb-6">
          <h3 className="text-lg font-semibold text-white mb-4">Preferencias (opcional)</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Idioma del canal</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white"
              >
                <option value="es">Español</option>
                <option value="en">Inglés</option>
                <option value="both">Ambos (multi-canal)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Temas que te interesan</label>
              <input
                type="text"
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                placeholder="ej: tecnología, finanzas, IA..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white placeholder-gray-500"
              />
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-sm text-gray-400 mb-1">Nichos a evitar</label>
            <input
              type="text"
              value={avoid}
              onChange={(e) => setAvoid(e.target.value)}
              placeholder="ej: gaming, música, contenido infantil"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white placeholder-gray-500"
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={deepScan}
              className="px-6 py-3 bg-green-600 hover:bg-green-500 text-white rounded-lg font-medium transition-colors text-sm"
            >
              🚀 Deep Scan (datos reales — recomendado)
            </button>
            <button
              onClick={discoverNiches}
              className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors text-sm"
            >
              ⚡ Scan rápido (IA + validación)
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Deep Scan busca en 50+ keywords reales de YouTube y encuentra outliers de canales pequeños.
            Tarda 1-2 minutos pero los datos son 100% reales.
          </p>
        </div>
      )}

      {/* Loading state */}
      {(status === 'discovering' || status === 'scanning' || status === 'ideas') && (
        <div className="bg-gray-900 rounded-xl p-12 text-center">
          <div className="animate-spin text-4xl mb-4">{status === 'scanning' ? '🔬' : '🔄'}</div>
          <p className="text-white text-lg font-medium">
            {status === 'scanning' ? 'Deep Scan en progreso...' :
             status === 'discovering' ? 'Analizando mercado de YouTube...' :
             'Generando ideas virales...'}
          </p>
          <p className="text-gray-400 text-sm mt-2">
            {status === 'scanning'
              ? scanProgress || 'Buscando outliers reales en 50+ keywords de alto RPM...'
              : status === 'discovering'
              ? 'Evaluando RPM, competencia, potencial de automatización y oportunidades actuales'
              : `Creando ideas optimizadas para "${selectedNiche?.name}"`}
          </p>
          <p className="text-gray-500 text-xs mt-4">
            {status === 'scanning' ? 'Esto puede tardar 1-2 minutos (buscando datos reales)' : 'Esto puede tardar 15-30 segundos'}
          </p>
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="bg-red-900/30 border border-red-800 rounded-xl p-6 mb-6">
          <p className="text-red-300">{error}</p>
          <button
            onClick={() => setStatus('idle')}
            className="mt-3 px-4 py-2 bg-gray-700 text-white rounded text-sm"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Summary */}
      {summary && (
        <div className="bg-gray-900 rounded-xl p-6 mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">Análisis del Mercado</h3>
          <p className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">{summary}</p>
        </div>
      )}

      {/* Niche results */}
      {niches.length > 0 && !selectedNiche && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Top {niches.length} Nichos</h3>
            <button
              onClick={() => { setNiches([]); setSummary(''); setStatus('idle') }}
              className="text-sm text-gray-400 hover:text-white"
            >
              Nueva búsqueda
            </button>
          </div>
          {niches.map((niche, i) => (
            <div
              key={i}
              className={`bg-gray-900 rounded-xl p-5 border-l-4 cursor-pointer hover:bg-gray-800/80 transition-colors ${
                i === 0 ? 'border-yellow-500' : i === 1 ? 'border-gray-400' : i === 2 ? 'border-orange-600' : 'border-gray-700'
              }`}
              onClick={() => loadIdeas(niche)}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-white">#{niche.rank}</span>
                    <h4 className="text-lg font-semibold text-white">{niche.name}</h4>
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{niche.rationale}</p>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-2xl font-bold text-green-400">{niche.rpm_estimate}</div>
                  <div className="text-xs text-gray-500">RPM</div>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-3 mb-3">
                <div className="bg-gray-800 rounded p-2 text-center">
                  <div className="text-xs text-gray-500">Competencia</div>
                  <div className={`font-bold ${niche.competition <= 3 ? 'text-green-400' : niche.competition <= 6 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {niche.competition}/10
                  </div>
                </div>
                <div className="bg-gray-800 rounded p-2 text-center">
                  <div className="text-xs text-gray-500">Producción</div>
                  <div className="font-bold text-blue-400">{niche.production_ease}/10</div>
                </div>
                <div className="bg-gray-800 rounded p-2 text-center">
                  <div className="text-xs text-gray-500">Automatización</div>
                  <div className="font-bold text-purple-400">{niche.ai_automation}/10</div>
                </div>
                <div className="bg-gray-800 rounded p-2 text-center">
                  <div className="text-xs text-gray-500">Score</div>
                  <div className="font-bold text-yellow-400">{niche.score}</div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 text-xs">
                <span className="bg-gray-800 text-gray-400 px-2 py-1 rounded">{niche.content_format}</span>
                <span className="bg-gray-800 text-gray-400 px-2 py-1 rounded">{niche.target_audience}</span>
                {niche.reference_channels?.slice(0, 2).map((ch, j) => (
                  <span key={j} className="bg-blue-900/30 text-blue-400 px-2 py-1 rounded">{ch}</span>
                ))}
              </div>

              <p className="text-xs text-yellow-500/70 mt-2">{niche.opportunity_window}</p>

              {(niche as any).validated && (
                <p className="text-xs text-green-500 mt-1">
                  ✓ Validado con YouTube API — {(niche as any).real_channels_found} canales reales encontrados
                  {(niche as any).real_top_channels?.map((c: any, j: number) => (
                    <span key={j} className="ml-2 text-gray-400">| {c.name} ({(c.subs/1000).toFixed(0)}K)</span>
                  ))}
                </p>
              )}

              <div className="mt-3 text-xs text-blue-400 font-medium">
                Haz clic para ver ideas de vídeo →
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Video ideas for selected niche */}
      {selectedNiche && ideas.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <button
                onClick={() => { setSelectedNiche(null); setIdeas([]) }}
                className="text-sm text-blue-400 hover:text-blue-300 mb-1"
              >
                ← Volver a nichos
              </button>
              <h3 className="text-lg font-semibold text-white">
                Ideas para: {selectedNiche.name}
              </h3>
            </div>
          </div>

          <div className="space-y-3">
            {ideas.map((idea, i) => (
              <div key={i} className="bg-gray-900 rounded-xl p-4 hover:bg-gray-800/80 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                        idea.viral_score >= 8 ? 'bg-green-600/20 text-green-400' :
                        idea.viral_score >= 6 ? 'bg-yellow-600/20 text-yellow-400' :
                        'bg-gray-700 text-gray-400'
                      }`}>
                        Viral: {idea.viral_score}/10
                      </span>
                      <span className="text-xs text-gray-500">{idea.duration_minutes} min</span>
                      <span className="text-xs text-gray-500">{idea.traffic_source}</span>
                      <span className="text-xs text-gray-500">{idea.content_type}</span>
                    </div>
                    <h4 className="text-white font-medium">{idea.title}</h4>
                    <p className="text-xs text-gray-500 mt-1 italic">Hook: "{idea.hook}"</p>
                    <p className="text-xs text-gray-400 mt-1">{idea.rationale}</p>
                    {idea.english_inspiration && (
                      <p className="text-xs text-blue-400/60 mt-1">Ref: {idea.english_inspiration}</p>
                    )}
                    <div className="flex gap-1 mt-2">
                      {idea.keywords?.map((kw, j) => (
                        <span key={j} className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">{kw}</span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={() => onCreateProject(idea.title, idea.title)}
                    className="shrink-0 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition-colors"
                  >
                    → Crear Proyecto
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
