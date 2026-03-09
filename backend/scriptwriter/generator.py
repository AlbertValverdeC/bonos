import json

from openai import OpenAI

from backend.config.settings import OPENAI_API_KEY, SCRIPTWRITER_MODEL, SCRIPTWRITER_TEMPERATURE
from backend.scriptwriter.prompts import SYSTEM_PROMPT, IDEA_SUGGESTION_PROMPT
from backend.storage.database import get_db
from backend.storage.models import Project, ScriptSection, ApiUsageLog


def generate_script(db, project_id: int, duration_minutes: int = 15, extra_instructions: str = ""):
    """Generate a script for a project using OpenAI."""
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    project.status = "scripting"
    db.commit()

    client = OpenAI(api_key=OPENAI_API_KEY)

    channel_context = ""
    if project.channel:
        channel_context = f"\nCanal: {project.channel.name}\nNicho: {project.channel.niche}\nEstilo: {project.channel.style_prompt}"

    user_prompt = f"""Genera un guion completo para un vídeo de YouTube de aproximadamente {duration_minutes} minutos.

Tema: {project.topic}
{channel_context}
{f"Instrucciones adicionales: {extra_instructions}" if extra_instructions else ""}

Recuerda: el hook debe ser impactante, incluir pattern interrupts cada 3-5 minutos, y cerrar con CTA."""

    response = client.chat.completions.create(
        model=SCRIPTWRITER_MODEL,
        temperature=SCRIPTWRITER_TEMPERATURE,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    script_data = json.loads(content)

    # Log API usage
    usage = response.usage
    log = ApiUsageLog(
        service="openai",
        endpoint=f"chat/{SCRIPTWRITER_MODEL}",
        tokens_input=usage.prompt_tokens if usage else 0,
        tokens_output=usage.completion_tokens if usage else 0,
        estimated_cost=_estimate_openai_cost(usage),
        project_id=project_id,
    )
    db.add(log)

    # Update project
    project.title = script_data.get("title", project.topic)
    project.script = content
    project.status = "script_review"
    project.current_step = 2
    project.metadata_json = json.dumps({
        "description": script_data.get("description", ""),
        "tags": script_data.get("tags", []),
    })

    # Clear old sections and create new ones
    db.query(ScriptSection).filter_by(project_id=project_id).delete()
    for i, section in enumerate(script_data.get("sections", [])):
        s = ScriptSection(
            project_id=project_id,
            position=i,
            section_type=section.get("type", "body"),
            narration_text=section.get("narration", ""),
            visual_instructions=section.get("visual", ""),
            duration_estimate=section.get("duration_estimate", 0),
        )
        db.add(s)

    db.commit()
    return {"title": project.title, "sections_count": len(script_data.get("sections", []))}


def suggest_ideas(niche: str, language: str = "es") -> list[dict]:
    """Suggest video ideas for a given niche."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=SCRIPTWRITER_MODEL,
        temperature=0.9,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": IDEA_SUGGESTION_PROMPT},
            {"role": "user", "content": f"Nicho: {niche}\nIdioma: {language}"},
        ],
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return data.get("ideas", [])


def _estimate_openai_cost(usage) -> float:
    if not usage:
        return 0.0
    # GPT-4o pricing (approx): $2.50/1M input, $10/1M output
    input_cost = (usage.prompt_tokens / 1_000_000) * 2.50
    output_cost = (usage.completion_tokens / 1_000_000) * 10.0
    return round(input_cost + output_cost, 4)
