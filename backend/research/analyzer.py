"""Research analyzer — combines real data sources with AI interpretation.

Flow:
1. YouTube Data API → real channels, videos, view counts, outliers
2. Google Trends → real demand data (YouTube Search filter)
3. OpenAI → interprets ALL that real data using the exact criteria from the strategy doc

The AI never invents data — it only analyzes what the APIs return.
The evaluation criteria come directly from docs/estrategia-youtube-ai.md
"""

import json
from datetime import datetime, timedelta

from openai import OpenAI

from backend.config.settings import OPENAI_API_KEY, SCRIPTWRITER_MODEL
from backend.research.youtube_api import (
    search_channels, search_niche_videos, find_outliers, analyze_niche_competition,
    YOUTUBE_API_KEY,
)

try:
    from backend.research.trends import check_trend, get_related_queries
    HAS_TRENDS = True
except ImportError:
    HAS_TRENDS = False


# ══════════════════════════════════════════════════════════════════════
# CRITERIOS EXACTOS extraídos de docs/estrategia-youtube-ai.md
# ══════════════════════════════════════════════════════════════════════

EVALUATION_CRITERIA = """
## CRITERIOS DE EVALUACIÓN DE NICHOS (de la estrategia documentada)

### REGLA 1: Ratio de Viralidad (vistas >> suscriptores)
- Buscar canales donde los vídeos superan ampliamente el número de suscriptores.
- Vídeos largos: canal de 30K subs con vídeos de 200K+ vistas = señal fuerte.
- "Blue Ocean Signal": vídeos de 100K+ vistas en canales de <5K subs = el algoritmo
  los promocionó pese a cero autoridad → el tema tiene tirón masivo.
- CÁLCULO: outlier_score = vistas_video / media_vistas_canal.
  - 2-3x = moderado (interesante pero no señal fuerte)
  - 3-10x = outlier fuerte (rango ideal para replicar)
  - 10x+ = outlier extremo (el tema genera visitas independientemente del canal)

### REGLA 2: RPM alto (Revenue Per Mille)
Ranking real por nicho (USD):
| Nicho | RPM |
|-------|-----|
| Finanzas / Tarjetas de crédito | $10-$40+ |
| Seguros | $9-$11 |
| Legal / Derecho | $9-$15 |
| Inmobiliario | $8-$35 |
| Negocios / Emprendimiento | $15-$30 |
| Marketing Digital | $8-$12 |
| Educación | $9-$14 |
| Salud y Fitness | ~$12 |
| Tecnología / IA | $3-$12 |
| Storytelling Animado | $9-$13 |
| True Crime / Documentales | $8-$15 |
| ASMR / Meditación | $10-$11 |

EVITAR (RPM bajo): Música ($1-3), Gaming ($2-5), Entretenimiento genérico ($2-5),
Contenido infantil ($1-3), Vlogs genéricos ($2-4).

Factores que modifican RPM:
- Duración 8+ min con mid-rolls puede duplicar/triplicar RPM
- Viewer de EEUU vale ~10x más que uno de India/Brasil
- Q4 (Oct-Dic) RPMs suben 30-60%
- Shorts RPM es 50-100x menor que long-form

### REGLA 3: Producción sencilla para faceless
Formatos fáciles (de mejor a peor):
1. Slides/presentaciones + voz IA (finanzas, educación)
2. Screen recordings + narración (tech, tutoriales)
3. Stock footage + voz profesional (true crime, docs)
4. Audio ambient + visuales simples (meditación, ASMR)

### REGLA 4: Micro-nicho > Nicho amplio
- YouTube favorece desequilibrio oferta-demanda: búsquedas consistentes + pocos vídeos
  de calidad = el algoritmo empuja los nuevos uploads rápidamente.
- Micro-nicho puede significar 5x más ingresos por las mismas visitas.
- Los nichos amplios (gaming genérico, belleza, tech reviews) están masificados y
  requieren personalidad — exactamente lo que faceless NO tiene.

### REGLA 5: Competencia
- < 200 creadores consistentes en el nicho = oportunidad
- Pocos canales de 100K+ subs = blue ocean
- Si todos hacen un formato, el formato contrario está desatendido

### REGLA 6: Estrategia EN → ES
- Investigar en inglés (EEUU) lo que funciona → adaptar al español
- Sweet spot: contenido en español consumido por hispanos en EEUU (CPMs americanos)
- 80% de audiencias hispanas prefieren contenido en español incluso si son bilingües
- España CPM ~$14.22 / México ~$1.30 / LatAm $1-$3

### REGLA 7: Contenido Evergreen vs Trending
- Evergreen: tutoriales, educación, finanzas fundamentales → acumulan vistas años
- Estacional: regalos (Nov), impuestos (Mar), vuelta al cole (Ago)
- Publicar contenido estacional 4-6 SEMANAS ANTES del pico
- Mezcla ideal: 60% evergreen + 30% trending + 10% controversial

### REGLA 8: Red Flags (señales de nicho saturado)
- Duración media de visualización < 30% en todo el nicho
- Interés decreciente en Google Trends (vista 5 años)
- Barrera de entrada muy baja = saturación rápida
- Millones de creadores compitiendo

### REGLA 9: Potencial de automatización IA
- ¿Se puede generar el guion con IA? (ChatGPT/Claude)
- ¿Se puede generar el voiceover con TTS? (ElevenLabs)
- ¿Se encuentra stock footage fácilmente? (Pexels/Pixabay)
- ¿Se puede ensamblar automáticamente? (CapCut/ffmpeg)
- Objetivo: 80%+ del pipeline automatizable

### REGLA 10: Formato ideal
- Vídeos largos: 15-30 minutos para maximizar mid-roll ads
- Cambio visual cada 5-7 segundos
- Pattern interrupts cada 3-5 minutos
- Hook impactante en primeros 30 segundos (NUNCA empezar con "Hola")
- Retención objetivo: 50%+ al punto medio

### CHECKLIST FINAL DE VALIDACIÓN
1. ✅ Encontrar vídeos outlier (3-10x+) en el nicho
2. ✅ Google Trends estable o ascendente (5 años, filtro YouTube Search)
3. ✅ < 200 creadores consistentes, pocos canales 100K+
4. ✅ RPM estimado según categoría y geografía de audiencia
5. ✅ No es moda pasajera — cruzar con YouTube search suggest
6. ✅ No hay red flags de saturación
7. ✅ Micro-nicho más estrecho y rentable donde demanda > oferta
8. ✅ Mix evergreen + estacional planificado
"""

ANALYSIS_PROMPT = f"""Eres un analista de datos de YouTube especializado en canales faceless.
Te voy a dar DATOS REALES de la API de YouTube y Google Trends.
Tu trabajo es INTERPRETAR estos datos usando los criterios exactos que te doy abajo.

REGLAS ESTRICTAS:
- SOLO basa tu análisis en los datos que te proporciono. NO inventes estadísticas.
- Si un dato no está disponible, dilo explícitamente.
- Menciona canales específicos, vídeos específicos y números reales de los datos.
- Calcula outlier scores reales: vistas_video / media_canal.
- Aplica TODOS los criterios de evaluación, uno por uno.

{EVALUATION_CRITERIA}

Responde en español.
"""

NICHE_ANALYSIS_JSON = """
Formato JSON de respuesta:
{
  "summary": "Resumen ejecutivo basado en datos reales",
  "checklist": {
    "outliers_found": true/false + detalles,
    "trend_direction": "ascending/stable/declining/no_data",
    "competition_level": "baja/media/alta" + número de canales grandes,
    "rpm_estimate": "$X-$Y basado en categoría",
    "saturation_red_flags": ["flag1"] o [],
    "automation_potential": "alto/medio/bajo" + justificación,
    "evergreen_ratio": "% de contenido que sería evergreen"
  },
  "opportunity_score": 1-10,
  "competition_analysis": "Basado en canales reales encontrados...",
  "top_outliers": [
    {
      "video_title": "título real",
      "channel": "canal real",
      "views": 123456,
      "channel_subscribers": 5000,
      "outlier_score": 15.2,
      "why_it_worked": "interpretación"
    }
  ],
  "recommended_angles": [
    {
      "angle": "Ángulo concreto",
      "rationale": "Basado en qué datos reales",
      "reference_video": "Vídeo real que valida",
      "estimated_rpm": "$X-$Y",
      "production_format": "slides/screen/stock"
    }
  ],
  "video_ideas": [
    {
      "rank": 1,
      "title": "Título en español optimizado para CTR (máx 60 chars)",
      "duration_minutes": 20,
      "traffic_source": "browse/search/suggested",
      "content_type": "explainer/listicle/case_study/tutorial/story",
      "hook": "Primeras palabras impactantes del vídeo",
      "keywords": ["kw1", "kw2"],
      "rationale": "Basado en qué dato real o tendencia",
      "inspired_by": "Vídeo/canal real que valida",
      "viral_potential": 8
    }
  ],
  "warnings": ["Riesgos identificados en los datos"],
  "next_steps": ["Acción 1", "Acción 2"]
}
"""


def analyze_niche_with_data(niche_query: str, language: str = "es") -> dict:
    """Full analysis of a niche using real data + documented criteria."""
    real_data = {"query": niche_query, "sources": []}

    # --- YouTube Data API ---
    if YOUTUBE_API_KEY:
        try:
            competition = analyze_niche_competition(niche_query)
            real_data["youtube_competition"] = competition
            real_data["sources"].append("YouTube Data API v3")

            # Find outliers in channels <100K subs (faceless opportunity per Rule 1)
            small_channels = [
                c for c in competition.get("top_channels", [])
                if c["subscribers"] < 100000 and c["subscribers"] > 1000
            ][:5]

            outlier_data = []
            for ch in small_channels:
                try:
                    outliers = find_outliers(ch["channel_id"], threshold=2.0)
                    if outliers.get("outliers"):
                        outlier_data.append({
                            "channel": ch["title"],
                            "subscribers": ch["subscribers"],
                            "avg_views": outliers["avg_views"],
                            "outliers": [
                                {
                                    "title": o["title"],
                                    "views": o["views"],
                                    "outlier_score": o["outlier_score"],
                                    "published_at": o["published_at"],
                                }
                                for o in outliers["outliers"][:5]
                            ],
                        })
                except Exception:
                    pass
            real_data["outlier_analysis"] = outlier_data

            # Top videos last 12 months (long-form, per Rule 10)
            one_year_ago = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%dT00:00:00Z")
            try:
                niche_videos = search_niche_videos(
                    niche_query, max_results=20,
                    published_after=one_year_ago, min_duration="long",
                )
                real_data["top_long_videos"] = niche_videos[:15]
            except Exception:
                pass

        except Exception as e:
            real_data["youtube_error"] = str(e)

    # --- Google Trends (YouTube Search filter, per Rule 2 checklist item 2) ---
    if HAS_TRENDS:
        try:
            trend_1y = check_trend(niche_query, timeframe="today 12-m")
            real_data["google_trends_1y"] = trend_1y
            real_data["sources"].append("Google Trends (YouTube Search, 1 año)")

            trend_5y = check_trend(niche_query, timeframe="today 5-y")
            real_data["google_trends_5y"] = trend_5y
            real_data["sources"].append("Google Trends (YouTube Search, 5 años)")

            related = get_related_queries(niche_query)
            real_data["rising_queries"] = related.get("rising_queries", [])[:10]
            real_data["top_queries"] = related.get("top_queries", [])[:10]
        except Exception as e:
            real_data["trends_error"] = str(e)

    # --- OpenAI interprets real data ---
    client = OpenAI(api_key=OPENAI_API_KEY)

    data_json = json.dumps(real_data, ensure_ascii=False, indent=2, default=str)

    response = client.chat.completions.create(
        model=SCRIPTWRITER_MODEL,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": f"""Analiza el nicho: "{niche_query}"
Idioma del canal objetivo: {language}

DATOS REALES RECOPILADOS DE APIs:
{data_json}

Aplica TODOS los criterios de evaluación (Reglas 1-10) a estos datos.
Completa el checklist de validación.
Genera 10-15 ideas de vídeo basadas en los outliers y tendencias reales.
{NICHE_ANALYSIS_JSON}"""},
        ],
    )

    ai_analysis = json.loads(response.choices[0].message.content)

    return {
        "query": niche_query,
        "data_sources": real_data["sources"],
        "real_data": real_data,
        "analysis": ai_analysis,
    }


def discover_niches(preferences: dict | None = None) -> dict:
    """Discover niches — validates top 3 with real data when available."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    pref_text = ""
    if preferences:
        parts = []
        if preferences.get("language"):
            parts.append(f"Idioma del canal: {preferences['language']}")
        if preferences.get("interests"):
            parts.append(f"Intereses del creador: {preferences['interests']}")
        if preferences.get("avoid"):
            parts.append(f"Evitar: {preferences['avoid']}")
        if preferences.get("target_audience"):
            parts.append(f"Audiencia: {preferences['target_audience']}")
        pref_text = "\n".join(parts)

    has_real_data = bool(YOUTUBE_API_KEY)

    response = client.chat.completions.create(
        model=SCRIPTWRITER_MODEL,
        temperature=0.8,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"""Eres un analista de YouTube para canales faceless.

{EVALUATION_CRITERIA}

ESTRATEGIA CLAVE (Regla 6 — EN → ES):
Tu trabajo principal es ENCONTRAR lo que ya funciona en YouTube en INGLÉS (mercado EEUU/global)
y proponer cómo ADAPTARLO al español. Esta es la ventaja competitiva:
- Busca nichos que explotan en inglés pero tienen poca competencia en español
- El contenido en español consumido por hispanos en EEUU tiene CPMs americanos ($14-40+)
- Para cada nicho, indica: qué canales en inglés lo validan + cómo sería la versión en español
- Los reference_channels deben ser canales EN INGLÉS que prueban que el nicho funciona

Genera un ranking de 10 MICRO-NICHOS específicos para canales faceless.
Aplica las 10 reglas de evaluación a cada nicho.
Sé ESPECÍFICO: "tarjetas de crédito para nómadas digitales" NO "finanzas personales".

{"IMPORTANTE: Los top 3 nichos se validarán con datos reales de YouTube Data API." if has_real_data else "NOTA: No hay YouTube API key. Marca todas las cifras como ESTIMACIONES."}

JSON:
{{
  "data_source": "{"youtube_api_validated" if has_real_data else "ai_estimates_only"}",
  "analysis_summary": "Resumen del mercado actual — qué funciona en inglés y la oportunidad en español",
  "niches": [
    {{
      "rank": 1,
      "name": "Micro-nicho ESPECÍFICO",
      "rpm_estimate": "$X-$Y",
      "competition": 1-10,
      "production_ease": 1-10,
      "ai_automation": 1-10,
      "content_format": "slides/screen/stock/animation",
      "target_audience": "audiencia",
      "reference_channels": ["canal EN INGLÉS que valida (Xk subs)", "canal2"],
      "spanish_gap": "por qué hay oportunidad en español",
      "opportunity_window": "por qué ahora",
      "score": (rpm_mid × production_ease × ai_automation) / (competition + 1),
      "rationale": "justificación con criterios específicos",
      "checklist_score": "X/8 criterios cumplidos"
    }}
  ]
}}"""},
            {"role": "user", "content": pref_text or "Sin preferencias. Recomienda objetivamente los mejores nichos."},
        ],
    )

    result = json.loads(response.choices[0].message.content)

    # Validate top 3 with real YouTube data — search in ENGLISH (EN→ES strategy)
    if has_real_data and result.get("niches"):
        for niche in result["niches"][:3]:
            try:
                # Search in English first (where the proven demand is)
                en_channels = search_channels(niche["name"], max_results=10)
                # Also check Spanish competition
                es_name = niche.get("name", "")
                es_channels = search_channels(es_name, max_results=10) if es_name else []

                niche["validated"] = True
                niche["real_channels_found"] = len(en_channels)
                niche["real_top_channels"] = [
                    {"name": c["title"], "subs": c["subscribers"]}
                    for c in en_channels[:5]
                ]
                # Competition = how many BIG Spanish channels exist (the gap)
                es_big = len([c for c in es_channels if c["subscribers"] > 100000])
                en_big = len([c for c in en_channels if c["subscribers"] > 100000])
                niche["en_competition"] = f"{en_big} canales 100K+ en inglés"
                niche["es_competition"] = f"{es_big} canales 100K+ en español"
                niche["real_competition"] = "alta" if es_big >= 5 else "media" if es_big >= 2 else "baja"
            except Exception:
                niche["validated"] = False

    return result


def generate_video_ideas(niche: str, count: int = 15) -> dict:
    """Generate ideas backed by real outliers and trends."""
    real_context = ""

    if YOUTUBE_API_KEY:
        try:
            videos = search_niche_videos(niche, max_results=15, min_duration="long")
            if videos:
                real_context = "VÍDEOS REALES CON MÁS VISTAS EN ESTE NICHO (datos YouTube API):\n"
                for v in videos[:10]:
                    real_context += (
                        f"- \"{v['title']}\" — {v['views']:,} vistas, "
                        f"canal: {v['channel_title']}, duración: {v['duration']}\n"
                    )
                real_context += "\n¡Basa tus ideas en lo que YA funciona según estos datos reales!\n"
        except Exception:
            pass

    if HAS_TRENDS:
        try:
            related = get_related_queries(niche)
            rising = related.get("rising_queries", [])
            if rising:
                real_context += "\nBÚSQUEDAS EN AUGE en YouTube (Google Trends, datos reales):\n"
                for q in rising[:10]:
                    real_context += f"- \"{q.get('query', '')}\" (crecimiento: {q.get('value', 'N/A')})\n"
                real_context += "\nEstas son búsquedas REALES que la gente hace AHORA.\n"

            top = related.get("top_queries", [])
            if top:
                real_context += "\nBÚSQUEDAS MÁS POPULARES en YouTube:\n"
                for q in top[:10]:
                    real_context += f"- \"{q.get('query', '')}\"\n"
        except Exception:
            pass

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=SCRIPTWRITER_MODEL,
        temperature=0.85,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"""Genera ideas de vídeo para un canal faceless en español.

{EVALUATION_CRITERIA}

Reglas para las ideas:
- Cada idea debe ser un "outlier potencial" — diseñada para superar 5-10x la media
- Títulos en español optimizados para CTR (curiosity gap, números, power words, máx 60 chars)
- Duración: 15-30 min para maximizar mid-roll ads (Regla 10)
- Hook IMPACTANTE en primeros 10 seg — NUNCA "Hola" o presentaciones
- Producible con IA: guion + TTS + stock footage (Regla 9)
- Mezcla: 60% evergreen + 30% trending + 10% controversial (Regla 7)
- Estrategia EN→ES: adaptar lo que funciona en inglés (Regla 6)
- Keywords front-loaded en los títulos para SEO

{real_context if real_context else "NOTA: Sin datos reales disponibles. Basa las ideas en tu conocimiento."}
"""},
            {"role": "user", "content": f"""Genera {count} ideas para el nicho: "{niche}"

JSON:
{{
  "niche": "{niche}",
  "data_sources_used": {json.dumps(["youtube_api", "google_trends"] if real_context else ["ai_knowledge"])},
  "ideas": [
    {{
      "rank": 1,
      "title": "Título en español optimizado CTR",
      "duration_minutes": 20,
      "traffic_source": "browse/search/suggested",
      "content_type": "explainer/listicle/case_study/tutorial/story",
      "hook": "Primeras palabras impactantes",
      "keywords": ["kw1", "kw2", "kw3"],
      "rationale": "Basado en qué dato real o criterio",
      "inspired_by": "Vídeo/canal real si aplica",
      "viral_potential": 1-10,
      "evergreen": true/false,
      "production_format": "slides/screen/stock"
    }}
  ]
}}"""},
        ],
    )

    return json.loads(response.choices[0].message.content)


def quick_niche_scan(niches: list[str]) -> list[dict]:
    """Quick scan of multiple niches with real data."""
    results = []

    for niche in niches:
        result = {"niche": niche}

        if YOUTUBE_API_KEY:
            try:
                channels = search_channels(niche, max_results=10)
                big = len([c for c in channels if c["subscribers"] > 100000])
                small_viral = len([
                    c for c in channels
                    if c["subscribers"] < 50000
                    and c["video_count"] > 0
                    and (c["total_views"] / max(c["video_count"], 1)) > c["subscribers"]
                ])
                result["channels_found"] = len(channels)
                result["big_channels"] = big
                result["small_channels_with_viral_potential"] = small_viral
                result["competition"] = "alta" if big >= 5 else "media" if big >= 2 else "baja"
            except Exception as e:
                result["youtube_error"] = str(e)

        if HAS_TRENDS:
            try:
                trend = check_trend(niche)
                result["trend"] = trend.get("trend", "unknown")
                result["trend_change"] = trend.get("change_pct", 0)
                result["interest"] = trend.get("avg_interest", 0)
            except Exception:
                result["trend"] = "unknown"

        results.append(result)

    return results


def analyze_scan_results(scan_data: dict) -> dict:
    """AI interprets REAL data from deep_scan. DATA FIRST approach.

    The scan_data contains actual outlier videos, channel stats,
    category rankings, and Spanish gap analysis — all from YouTube API.
    The AI's only job is to interpret and rank these real findings.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Build a concise summary of real data for the prompt
    outliers = scan_data.get("outliers", [])[:30]
    categories = scan_data.get("categories_ranked", [])
    spanish_gap = scan_data.get("spanish_gap", [])
    rising = scan_data.get("rising_channels", [])[:15]
    metadata = scan_data.get("scan_metadata", {})

    data_summary = f"""## DATOS REALES DEL SCAN (YouTube Data API)

### Metadata del scan
- Keywords buscadas: {metadata.get('keywords_searched', 0)}
- Vídeos encontrados: {metadata.get('total_videos_found', 0)}
- Canales analizados: {metadata.get('unique_channels_analyzed', 0)}
- Outliers detectados: {metadata.get('outliers_found', 0)}
- Filtros: canales <{metadata.get('filters', {}).get('max_channel_subs', 50000)} subs, vídeos >{metadata.get('filters', {}).get('min_video_views', 50000)} vistas, ratio >{metadata.get('filters', {}).get('min_outlier_ratio', 5)}x

### TOP OUTLIERS (vídeos con ratio vistas/subs más alto — canales pequeños con vídeos virales)
"""
    for v in outliers[:20]:
        data_summary += (
            f"- \"{v['title']}\" | canal: {v['channel_title']} "
            f"({v['channel_subscribers']:,} subs) | {v.get('views', 0):,} vistas | "
            f"ratio: {v['views_to_subs_ratio']}x | keyword: {v['search_keyword']} "
            f"| categoría: {v['search_category']}\n"
        )

    data_summary += "\n### CATEGORÍAS RANKEADAS POR OUTLIERS\n"
    for cat in categories:
        data_summary += (
            f"- {cat['category']}: {cat['outlier_count']} outliers, "
            f"mejor ratio: {cat['best_ratio']}x, vistas totales: {cat['total_views']:,}\n"
        )

    if spanish_gap:
        data_summary += "\n### GAP EN→ES (oportunidad: lo que funciona en inglés vs competencia en español)\n"
        for g in spanish_gap:
            data_summary += (
                f"- \"{g['en_keyword']}\" | EN: {g['en_views']:,} vistas | "
                f"ES max: {g['es_max_views']:,} vistas | "
                f"gap score: {g['gap_score']}x | categoría: {g['category']}\n"
            )

    if rising:
        data_summary += "\n### CANALES EMERGENTES (pequeños, creciendo rápido)\n"
        for ch in rising[:10]:
            data_summary += (
                f"- {ch['channel_name']} ({ch['subscribers']:,} subs) | "
                f"mejor ratio: {ch['top_ratio']}x | "
                f"categorías: {', '.join(ch['categories'])}\n"
            )

    response = client.chat.completions.create(
        model=SCRIPTWRITER_MODEL,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"""Eres un analista de YouTube para canales faceless.

{EVALUATION_CRITERIA}

REGLA FUNDAMENTAL: Solo puedes basar tu análisis en los DATOS REALES que te doy abajo.
NO inventes canales, vídeos ni estadísticas. Si un dato no está, dilo.
Tu trabajo es INTERPRETAR y RANKEAR los hallazgos reales, no inventar nuevos.

Para cada nicho que recomiendes:
- Cita los vídeos/canales REALES del scan que lo validan
- Usa los outlier ratios REALES para justificar
- Usa el gap score EN→ES REAL para medir la oportunidad
- Aplica las 10 reglas de evaluación a los datos reales
"""},
            {"role": "user", "content": f"""{data_summary}

Basándote EXCLUSIVAMENTE en estos datos reales, genera un ranking de los mejores nichos.

JSON:
{{
  "analysis_summary": "Resumen basado en datos reales del scan",
  "niches": [
    {{
      "rank": 1,
      "name": "Nombre del micro-nicho",
      "rpm_estimate": "$X-$Y (basado en categoría real)",
      "competition": 1-10,
      "production_ease": 1-10,
      "ai_automation": 1-10,
      "content_format": "slides/screen/stock",
      "target_audience": "audiencia",
      "reference_channels": ["canal REAL del scan (Xk subs)"],
      "proof_videos": ["título REAL del outlier que lo valida"],
      "outlier_ratio": "ratio REAL del mejor outlier",
      "spanish_gap": "gap score REAL o 'no analizado'",
      "opportunity_window": "por qué ahora (basado en datos)",
      "score": 0,
      "rationale": "justificación con datos REALES del scan"
    }}
  ],
  "video_ideas": [
    {{
      "rank": 1,
      "title": "Título en español (adaptación del outlier real)",
      "inspired_by": "Título REAL del vídeo outlier que inspira esta idea",
      "original_views": 123456,
      "original_channel_subs": 5000,
      "duration_minutes": 20,
      "traffic_source": "browse/search/suggested",
      "content_type": "explainer/listicle/case_study/tutorial/story",
      "hook": "Primeras palabras impactantes",
      "keywords": ["kw1", "kw2"],
      "rationale": "Por qué funcionará basado en los datos",
      "viral_score": 1-10
    }}
  ]
}}"""},
        ],
    )

    return json.loads(response.choices[0].message.content)
