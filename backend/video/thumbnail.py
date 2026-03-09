import requests
from pathlib import Path

from openai import OpenAI

from backend.config.settings import OPENAI_API_KEY, THUMBNAILS_DIR
from backend.storage.models import Project, ApiUsageLog


def generate_thumbnail(db, project_id: int):
    """Generate a YouTube thumbnail using DALL-E."""
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    project.status = "thumbnail"
    db.commit()

    client = OpenAI(api_key=OPENAI_API_KEY)

    channel_style = ""
    if project.channel and project.channel.thumbnail_style:
        channel_style = f"\nEstilo del canal: {project.channel.thumbnail_style}"

    prompt = f"""Create a YouTube thumbnail for a video titled: "{project.title}"

Requirements:
- Bold, high-contrast design optimized for CTR
- 0-3 words of large, bold text maximum
- Warm colors (reds, oranges, yellows) preferred
- Clean composition, readable at small size (mobile)
- Professional, modern style
- NO faces (faceless channel)
- Strong visual storytelling - communicate the topic through icons, graphics, or dramatic imagery
{channel_style}

Style: Professional YouTube thumbnail, high contrast, bold text, 16:9 aspect ratio"""

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",  # Closest to 16:9
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url

    # Download the image
    filename = f"project_{project_id}_thumb.png"
    filepath = THUMBNAILS_DIR / filename

    img_resp = requests.get(image_url, timeout=60)
    img_resp.raise_for_status()
    filepath.write_bytes(img_resp.content)

    # Log API usage (~$0.04 per standard image)
    log = ApiUsageLog(
        service="openai",
        endpoint="images/dall-e-3",
        estimated_cost=0.04,
        project_id=project_id,
    )
    db.add(log)

    project.thumbnail_filename = filename
    project.status = "ready_to_upload"
    project.current_step = 7
    db.commit()

    return {"filename": filename}
