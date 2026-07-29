"""Cloud-injectable request builders and lifecycle runner for Chapter 13.

This module only imports the Google Cloud SDK inside factory functions.  A
``--dry-run`` caller can therefore construct and inspect every request without
creating credentials, a client, a network connection, or cloud resources.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from building_simulator import BuildingEnvironmentSimulator

PROJECT_RE = re.compile(r"^[a-z][a-z0-9-]{4,61}[a-z0-9]$")
LOCATION_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*[0-9]+$")
STUDY_NAME_RE = re.compile(r"^projects/[^/]+/locations/[^/]+/studies/[^/]+$")


class VizierClient(Protocol):
    def create_study(self, *, parent: str, study: Mapping[str, Any]) -> Any: ...
    def suggest_trials(self, *, parent: str, suggestion_count: int, client_id: str) -> Any: ...
    def add_trial_measurement(self, request: Mapping[str, Any]) -> Any: ...
    def complete_trial(self, request: Mapping[str, Any]) -> Any: ...
    def list_optimal_trials(self, *, parent: str) -> Any: ...
    def delete_study(self, *, name: str) -> Any: ...


@dataclass(frozen=True)
class CloudSettings:
    project: str
    location: str
    experiment: str
    client_id: str = "chapter-13-sample"

    @property
    def parent(self) -> str:
        return f"projects/{self.project}/locations/{self.location}"

    def validate(self) -> None:
        if not PROJECT_RE.fullmatch(self.project):
            raise ValueError(
                "project must be a Google Cloud project ID, supplied by --project "
                "or GOOGLE_CLOUD_PROJECT"
            )
        if not LOCATION_RE.fullmatch(self.location):
            raise ValueError("location must look like a regional location, for example us-central1")
        if not self.experiment.strip():
            raise ValueError("experiment is required")
        if not self.client_id.strip():
            raise ValueError("client_id is required")


def settings_from_args(args: Any) -> CloudSettings:
    project = args.project or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location = args.location or os.environ.get("GOOGLE_CLOUD_LOCATION", "")
    settings = CloudSettings(project, location, args.experiment, args.client_id)
    settings.validate()
    return settings


def discrete_parameter(parameter_id: str, values: Iterable[float]) -> dict[str, Any]:
    numeric_values = [float(value) for value in values]
    if not numeric_values:
        raise ValueError(f"{parameter_id} requires at least one value")
    return {"parameter_id": parameter_id, "discrete_value_spec": {"values": numeric_values}}


def continuous_parameter(parameter_id: str, minimum: float, maximum: float) -> dict[str, Any]:
    if not minimum < maximum:
        raise ValueError(f"{parameter_id} minimum must be less than maximum")
    return {
        "parameter_id": parameter_id,
        "double_value_spec": {"min_value": minimum, "max_value": maximum},
    }


def build_study_config(step: str, display_name: str) -> dict[str, Any]:
    if not display_name.strip():
        raise ValueError("study display name is required")
    if step == "grid":
        algorithm = "GRID_SEARCH"
        parameters = [discrete_parameter("ac_temp", [18, 20, 22, 24, 26, 28, 30])]
        metrics = [{"metric_id": "cost", "goal": "MINIMIZE"}]
    elif step == "bayesian":
        algorithm = "ALGORITHM_UNSPECIFIED"
        parameters = [
            continuous_parameter("ac_temp", 18.0, 30.0),
            continuous_parameter("insulation_thickness", 0.0, 20.0),
        ]
        metrics = [{"metric_id": "cost", "goal": "MINIMIZE"}]
    elif step == "multi_objective":
        algorithm = "ALGORITHM_UNSPECIFIED"
        parameters = [
            continuous_parameter("ac_temp", 18.0, 30.0),
            continuous_parameter("insulation_thickness", 0.0, 20.0),
            continuous_parameter("window_size", 1.0, 10.0),
            continuous_parameter("occupancy_density", 10.0, 100.0),
        ]
        metrics = [
            {"metric_id": "cost", "goal": "MINIMIZE"},
            {"metric_id": "comfort", "goal": "MAXIMIZE"},
        ]
    else:
        raise ValueError(f"unknown step: {step}")
    return {
        "display_name": display_name,
        "study_spec": {"algorithm": algorithm, "parameters": parameters, "metrics": metrics},
    }


def build_create_study_request(settings: CloudSettings, study: Mapping[str, Any]) -> dict[str, Any]:
    return {"parent": settings.parent, "study": dict(study)}


def build_suggest_trials_request(study_name: str, client_id: str) -> dict[str, Any]:
    validate_study_name(study_name)
    return {"parent": study_name, "suggestion_count": 1, "client_id": client_id}


def build_measurement_request(trial_name: str, metrics: Mapping[str, float]) -> dict[str, Any]:
    if not trial_name:
        raise ValueError("trial name is required")
    if not metrics:
        raise ValueError("at least one metric is required")
    return {
        "trial_name": trial_name,
        "measurement": {
            "metrics": [{"metric_id": key, "value": float(value)} for key, value in metrics.items()]
        },
    }


def build_complete_trial_request(trial_name: str, metrics: Mapping[str, float]) -> dict[str, Any]:
    if not trial_name:
        raise ValueError("trial name is required")
    return {
        "name": trial_name,
        "final_measurement": {
            "metrics": [{"metric_id": key, "value": float(value)} for key, value in metrics.items()]
        },
    }


def validate_study_name(study_name: str) -> None:
    if not STUDY_NAME_RE.fullmatch(study_name):
        raise ValueError("study_name must be projects/PROJECT/locations/LOCATION/studies/STUDY_ID")


def validate_study_matches(settings: CloudSettings, study_name: str) -> None:
    """Reject cross-project or cross-location Study reuse."""
    validate_study_name(study_name)
    if not study_name.startswith(f"{settings.parent}/studies/"):
        raise ValueError("study_name project/location must match --project and --location")


def create_vizier_client(location: str) -> Any:
    """Create a client only for an explicitly confirmed cloud operation."""
    try:
        from google.cloud import aiplatform_v1
    except ImportError as exc:
        raise RuntimeError("install google-cloud-aiplatform before a cloud run") from exc
    return aiplatform_v1.VizierServiceClient(
        client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    )


def create_experiments_module() -> Any:
    try:
        from google.cloud import aiplatform
    except ImportError as exc:
        raise RuntimeError("install google-cloud-aiplatform before a cloud run") from exc
    return aiplatform


def _field(value: Any, name: str) -> Any:
    return value[name] if isinstance(value, Mapping) else getattr(value, name)


def trial_parameters(trial: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    for parameter in _field(trial, "parameters"):
        parameter_id = _field(parameter, "parameter_id")
        value = _field(parameter, "value")
        number_value = value["number_value"] if isinstance(value, Mapping) else value.number_value
        result[parameter_id] = float(number_value)
    return result


def trial_name(trial: Any) -> str:
    return str(_field(trial, "name"))


def initialize_experiment(experiments: Any, settings: CloudSettings) -> None:
    experiments.init(
        project=settings.project, location=settings.location, experiment=settings.experiment
    )


def log_experiment(
    experiments: Any, run_name: str, params: Mapping[str, float], metrics: Mapping[str, float]
) -> None:
    with experiments.start_run(run_name):
        experiments.log_params(dict(params))
        experiments.log_metrics(dict(metrics))


def evaluate_trial(
    step: str, simulator: BuildingEnvironmentSimulator, params: Mapping[str, float]
) -> dict[str, float]:
    if step == "grid":
        cost = simulator.calculate_cost(params["ac_temp"], 10.0, 5.0, 50.0)
        return {"cost": cost}
    if step == "bayesian":
        cost = simulator.calculate_cost(
            params["ac_temp"], params["insulation_thickness"], 5.0, 50.0
        )
        return {"cost": cost}
    if step == "multi_objective":
        cost = simulator.calculate_cost(
            params["ac_temp"],
            params["insulation_thickness"],
            params["window_size"],
            params["occupancy_density"],
        )
        return {
            "cost": cost,
            "comfort": simulator.calculate_comfort(params["ac_temp"], params["window_size"]),
        }
    raise ValueError(f"unknown step: {step}")


@dataclass(frozen=True)
class WorkflowResult:
    study_name: str | None
    completed_trials: int
    optimal_trials: tuple[Any, ...]
    dry_run_plan: dict[str, Any] | None = None


def run_workflow(
    *,
    step: str,
    settings: CloudSettings,
    display_name: str,
    trial_count: int,
    seed: int | None,
    dry_run: bool,
    existing_study_name: str | None = None,
    client_factory: Callable[[str], VizierClient] = create_vizier_client,
    experiments_factory: Callable[[], Any] = create_experiments_module,
) -> WorkflowResult:
    settings.validate()
    if trial_count < 1:
        raise ValueError("trial_count must be at least 1")
    study = build_study_config(step, display_name)
    create_request = build_create_study_request(settings, study)
    if existing_study_name:
        validate_study_matches(settings, existing_study_name)
    if dry_run:
        return WorkflowResult(
            study_name=existing_study_name,
            completed_trials=0,
            optimal_trials=(),
            dry_run_plan={
                "step": step,
                "trial_count": trial_count,
                "create_study": None if existing_study_name else create_request,
                "reuse_study": existing_study_name,
                "study_config": study,
                "experiment": settings.experiment,
                "network": "not used",
            },
        )

    client = client_factory(settings.location)
    experiments = experiments_factory()
    initialize_experiment(experiments, settings)
    if existing_study_name:
        study_name = existing_study_name
    else:
        created = client.create_study(**create_request)
        study_name = str(_field(created, "name"))
        validate_study_name(study_name)

    simulator = BuildingEnvironmentSimulator(seed=seed)
    completed = 0
    for _index in range(trial_count):
        suggestion = client.suggest_trials(
            **build_suggest_trials_request(study_name, settings.client_id)
        )
        trials = _field(suggestion.result(), "trials")
        for trial in trials:
            name = trial_name(trial)
            try:
                params = trial_parameters(trial)
                metrics = evaluate_trial(step, simulator, params)
                resource_parts = name.split("/")
                run_name = f"{step}-{resource_parts[-3]}-{resource_parts[-1]}"
                log_experiment(experiments, run_name, params, metrics)
                if step == "grid":
                    client.add_trial_measurement(build_measurement_request(name, metrics))
                    client.complete_trial({"name": name})
                else:
                    client.complete_trial(build_complete_trial_request(name, metrics))
                completed += 1
            except Exception as exc:
                raise RuntimeError(
                    f"Trial {name} may remain ACTIVE; inspect it before retry or cleanup"
                ) from exc
    optimal = tuple(_field(client.list_optimal_trials(parent=study_name), "optimal_trials"))
    return WorkflowResult(study_name, completed, optimal)


def render_dry_run(result: WorkflowResult) -> str:
    if result.dry_run_plan is None:
        raise ValueError("result is not a dry-run result")
    return json.dumps(result.dry_run_plan, indent=2, sort_keys=True)
