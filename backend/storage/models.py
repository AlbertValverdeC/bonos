from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    niche = Column(String(100), default="")
    language = Column(String(10), default="es")
    youtube_channel_id = Column(String(50), default="")
    voice_id = Column(String(100), default="")
    style_prompt = Column(Text, default="")
    thumbnail_style = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

    projects = relationship("Project", back_populates="channel", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "niche": self.niche,
            "language": self.language,
            "youtube_channel_id": self.youtube_channel_id,
            "voice_id": self.voice_id,
            "style_prompt": self.style_prompt,
            "thumbnail_style": self.thumbnail_style,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Project(Base):
    __tablename__ = "projects"

    STATUSES = [
        "idea", "scripting", "script_review", "voiceover",
        "footage", "assembling", "thumbnail",
        "ready_to_upload", "uploading", "published", "error",
    ]

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    title = Column(String(500), default="")
    topic = Column(String(500), nullable=False)
    status = Column(String(30), default="idea")
    current_step = Column(Integer, default=0)
    script = Column(Text, default="")
    script_approved = Column(Integer, default=0)
    audio_filename = Column(String(200), default="")
    audio_duration = Column(Float, default=0.0)
    video_filename = Column(String(200), default="")
    thumbnail_filename = Column(String(200), default="")
    youtube_video_id = Column(String(50), default="")
    youtube_url = Column(String(200), default="")
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, default="{}")
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    channel = relationship("Channel", back_populates="projects")
    sections = relationship("ScriptSection", back_populates="project", cascade="all, delete-orphan",
                            order_by="ScriptSection.position")
    footage_clips = relationship("FootageClip", back_populates="project", cascade="all, delete-orphan")
    pipeline_runs = relationship("PipelineRun", back_populates="project", cascade="all, delete-orphan",
                                 order_by="PipelineRun.started_at.desc()")

    def to_dict(self, include_sections=False, include_footage=False):
        d = {
            "id": self.id,
            "channel_id": self.channel_id,
            "title": self.title,
            "topic": self.topic,
            "status": self.status,
            "current_step": self.current_step,
            "script": self.script,
            "script_approved": bool(self.script_approved),
            "audio_filename": self.audio_filename,
            "audio_duration": self.audio_duration,
            "video_filename": self.video_filename,
            "thumbnail_filename": self.thumbnail_filename,
            "youtube_video_id": self.youtube_video_id,
            "youtube_url": self.youtube_url,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sections:
            d["sections"] = [s.to_dict() for s in self.sections]
        if include_footage:
            d["footage_clips"] = [f.to_dict() for f in self.footage_clips]
        return d


class ScriptSection(Base):
    __tablename__ = "script_sections"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    position = Column(Integer, default=0)
    section_type = Column(String(30), default="body")
    narration_text = Column(Text, default="")
    visual_instructions = Column(Text, default="")
    duration_estimate = Column(Float, default=0.0)

    project = relationship("Project", back_populates="sections")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "position": self.position,
            "section_type": self.section_type,
            "narration_text": self.narration_text,
            "visual_instructions": self.visual_instructions,
            "duration_estimate": self.duration_estimate,
        }


class FootageClip(Base):
    __tablename__ = "footage_clips"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("script_sections.id"), nullable=True)
    source = Column(String(30), default="pexels")
    source_id = Column(String(100), default="")
    source_url = Column(Text, default="")
    local_filename = Column(String(200), default="")
    duration = Column(Float, default=0.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    search_query = Column(String(200), default="")
    selected = Column(Integer, default=0)

    project = relationship("Project", back_populates="footage_clips")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "section_id": self.section_id,
            "source": self.source,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "local_filename": self.local_filename,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "search_query": self.search_query,
            "selected": bool(self.selected),
        }


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    step_name = Column(String(50), nullable=False)
    status = Column(String(20), default="running")
    started_at = Column(DateTime, default=utcnow)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, default="")
    details_json = Column(Text, default="{}")

    project = relationship("Project", back_populates="pipeline_runs")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "step_name": self.step_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error_message": self.error_message,
        }


class ApiUsageLog(Base):
    __tablename__ = "api_usage_log"

    id = Column(Integer, primary_key=True)
    service = Column(String(50), nullable=False)
    endpoint = Column(String(100), default="")
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    characters = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
