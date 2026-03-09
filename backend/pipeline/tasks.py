import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from backend.pipeline.event_bus import event_bus
from backend.storage.database import get_db
from backend.storage.models import Project, PipelineRun

executor = ThreadPoolExecutor(max_workers=2)


def run_pipeline_step(project_id: int, step_name: str, step_fn, **kwargs):
    """Submit a pipeline step to run in background."""
    executor.submit(_execute_step, project_id, step_name, step_fn, **kwargs)


def _execute_step(project_id: int, step_name: str, step_fn, **kwargs):
    db = get_db()
    try:
        run = PipelineRun(
            project_id=project_id,
            step_name=step_name,
            status="running",
        )
        db.add(run)
        db.commit()

        event_bus.emit("pipeline:step_start", {
            "project_id": project_id,
            "step": step_name,
        })

        result = step_fn(db, project_id, **kwargs)

        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

        event_bus.emit("pipeline:step_complete", {
            "project_id": project_id,
            "step": step_name,
            "result": result or {},
        })

    except Exception as e:
        tb = traceback.format_exc()
        run.status = "error"
        run.error_message = str(e)
        run.finished_at = datetime.now(timezone.utc)

        project = db.query(Project).get(project_id)
        if project:
            project.status = "error"
            project.error_message = f"[{step_name}] {str(e)}"

        db.commit()

        event_bus.emit("pipeline:step_error", {
            "project_id": project_id,
            "step": step_name,
            "error": str(e),
        })
        print(f"Pipeline error [{step_name}] project {project_id}:\n{tb}")
    finally:
        db.close()
