import unittest
from types import SimpleNamespace

from vizier_runner import (
    CloudSettings,
    build_complete_trial_request,
    build_study_config,
    run_workflow,
    validate_study_matches,
    validate_study_name,
)


class VizierRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = CloudSettings("sample-project", "us-central1", "ch13-test")

    def test_request_builders_match_each_step(self) -> None:
        grid = build_study_config("grid", "grid")
        self.assertEqual(grid["study_spec"]["algorithm"], "GRID_SEARCH")
        self.assertEqual(
            grid["study_spec"]["parameters"][0]["discrete_value_spec"]["values"],
            [18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 30.0],
        )
        multi = build_study_config("multi_objective", "multi")
        self.assertEqual(len(multi["study_spec"]["parameters"]), 4)
        self.assertEqual(
            [metric["goal"] for metric in multi["study_spec"]["metrics"]], ["MINIMIZE", "MAXIMIZE"]
        )
        self.assertEqual(
            build_complete_trial_request("trial", {"cost": 1})["final_measurement"]["metrics"][0][
                "metric_id"
            ],
            "cost",
        )

    def test_dry_run_never_creates_clients_or_network_connections(self) -> None:
        def prohibited(_: str):
            raise AssertionError("client factory must not be called in dry-run")

        first = run_workflow(
            step="grid",
            settings=self.settings,
            display_name="grid",
            trial_count=7,
            seed=1,
            dry_run=True,
            client_factory=prohibited,
        )
        second = run_workflow(
            step="grid",
            settings=self.settings,
            display_name="grid",
            trial_count=7,
            seed=1,
            dry_run=True,
            client_factory=prohibited,
        )
        self.assertEqual(first.dry_run_plan, second.dry_run_plan)
        plan = first.dry_run_plan
        assert plan is not None
        self.assertEqual(plan["network"], "not used")

    def test_explicit_study_reuse_adds_distinct_mock_trials_without_create(self) -> None:
        client = FakeClient()
        experiments = FakeExperiments()
        existing = "projects/sample-project/locations/us-central1/studies/existing"
        for _ in range(2):
            result = run_workflow(
                step="grid",
                settings=self.settings,
                display_name="ignored",
                trial_count=1,
                seed=8,
                dry_run=False,
                existing_study_name=existing,
                client_factory=lambda _: client,
                experiments_factory=lambda: experiments,
            )
            self.assertEqual(result.study_name, existing)
        self.assertEqual(client.create_calls, 0)
        self.assertEqual(client.measurements, 2)
        self.assertEqual(len(set(experiments.run_names)), 2)
        self.assertTrue(all(request["parent"] == existing for request in client.suggest_requests))

    def test_study_reuse_must_match_settings(self) -> None:
        with self.assertRaisesRegex(ValueError, "must match"):
            validate_study_matches(
                self.settings,
                "projects/other-project/locations/us-central1/studies/existing",
            )

    def test_failure_reports_the_active_trial_resource(self) -> None:
        client = FakeClient()
        experiments = FakeExperiments(fail_logging=True)
        existing = "projects/sample-project/locations/us-central1/studies/existing"
        with self.assertRaisesRegex(RuntimeError, r"trials/1.*ACTIVE"):
            run_workflow(
                step="grid",
                settings=self.settings,
                display_name="ignored",
                trial_count=1,
                seed=8,
                dry_run=False,
                existing_study_name=existing,
                client_factory=lambda _: client,
                experiments_factory=lambda: experiments,
            )
        self.assertEqual(client.measurements, 0)

    def test_invalid_study_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_study_name("studies/wildcard-*")


class FakeClient:
    def __init__(self) -> None:
        self.create_calls = 0
        self.measurements = 0
        self.suggestions = 0
        self.suggest_requests: list[dict[str, object]] = []

    def create_study(self, **_: object) -> object:
        self.create_calls += 1
        return SimpleNamespace(name="projects/sample-project/locations/us-central1/studies/new")

    def suggest_trials(self, **request: object) -> object:
        self.suggestions += 1
        self.suggest_requests.append(request)
        parameter = SimpleNamespace(
            parameter_id="ac_temp", value=SimpleNamespace(number_value=24.0)
        )
        trial = SimpleNamespace(
            name=(
                "projects/sample-project/locations/us-central1/studies/existing/trials/"
                f"{self.suggestions}"
            ),
            parameters=[parameter],
        )
        return SimpleNamespace(result=lambda: SimpleNamespace(trials=[trial]))

    def add_trial_measurement(self, request: object) -> None:
        self.measurements += 1

    def complete_trial(self, request: object) -> None:
        return None

    def list_optimal_trials(self, **_: object) -> object:
        return SimpleNamespace(optimal_trials=[])

    def delete_study(self, *, name: str) -> None:
        return None


class FakeExperiments:
    def __init__(self, fail_logging: bool = False) -> None:
        self.fail_logging = fail_logging
        self.run_names: list[str] = []

    def init(self, **_: object) -> None:
        return None

    def start_run(self, name: str) -> "FakeExperiments":
        self.run_names.append(name)
        return self

    def __enter__(self) -> "FakeExperiments":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def log_params(self, _: object) -> None:
        if self.fail_logging:
            raise RuntimeError("mock logging failure")
        return None

    def log_metrics(self, _: object) -> None:
        return None
