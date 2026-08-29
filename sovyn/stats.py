from dataclasses import dataclass
from datetime import UTC, datetime

from sovyn.storage import Store


@dataclass(frozen=True, slots=True)
class RunMetric:
    kind: str
    model_calls: int
    tool_calls: int
    workflow_reuse: bool
    zero_model: bool
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class LocalStats:
    tasks_completed: int
    workflows_reused: int
    model_calls: int
    zero_model_runs: int
    workflow_matches: int = 0
    workflow_repairs: int = 0
    workflow_evolutions: int = 0
    repair_model_calls: int = 0


def record_metric(store: Store, metric: RunMetric) -> None:
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO run_metrics "
            "(kind, model_calls, tool_calls, workflow_reuse, zero_model, duration_seconds, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                metric.kind,
                metric.model_calls,
                metric.tool_calls,
                int(metric.workflow_reuse),
                int(metric.zero_model),
                metric.duration_seconds,
                datetime.now(UTC).isoformat(),
            ),
        )
        connection.commit()


def record_workflow_event(store: Store, event: str, workflow: str, model_calls: int = 0) -> None:
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO workflow_events (event, workflow, model_calls, created_at) VALUES (?, ?, ?, ?)",
            (event, workflow, model_calls, datetime.now(UTC).isoformat()),
        )
        connection.commit()


def local_stats(store: Store) -> LocalStats:
    with store.connect() as connection:
        sessions = connection.execute("SELECT COUNT(*) FROM sessions WHERE result = 'success'").fetchone()
        metrics = connection.execute(
            "SELECT COALESCE(SUM(workflow_reuse), 0), COALESCE(SUM(model_calls), 0), "
            "COALESCE(SUM(zero_model), 0) FROM run_metrics"
        ).fetchone()
        events = {
            str(row[0]): (int(row[1]), int(row[2]))
            for row in connection.execute(
                "SELECT event, COUNT(*), COALESCE(SUM(model_calls), 0) FROM workflow_events GROUP BY event"
            ).fetchall()
        }
    return LocalStats(
        tasks_completed=int(sessions[0]),
        workflows_reused=int(metrics[0]),
        model_calls=int(metrics[1]),
        zero_model_runs=int(metrics[2]),
        workflow_matches=events.get("match", (0, 0))[0],
        workflow_repairs=events.get("repair", (0, 0))[0],
        workflow_evolutions=events.get("evolution", (0, 0))[0],
        repair_model_calls=events.get("repair", (0, 0))[1],
    )


def render_stats(store: Store) -> str:
    stats = local_stats(store)
    return "\n".join(
        (
            "SOVYN",
            "",
            f"Tasks completed        {stats.tasks_completed}",
            f"Workflows reused       {stats.workflows_reused}",
            f"Model calls            {stats.model_calls}",
            f"Zero-model runs        {stats.zero_model_runs}",
            f"Workflow matches       {stats.workflow_matches}",
            f"Workflow repairs       {stats.workflow_repairs}",
            f"Workflow evolutions    {stats.workflow_evolutions}",
        )
    )
