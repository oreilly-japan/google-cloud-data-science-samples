import unittest
from importlib import import_module

from cleanup import delete_study

analysis = import_module("04_surrogate_analysis")


class CleanupAndAnalysisTest(unittest.TestCase):
    STUDY = "projects/sample-project/locations/us-central1/studies/to-delete"

    def test_cleanup_dry_run_and_confirmation_guard(self) -> None:
        self.assertIn(
            "would delete",
            delete_study(
                client=None,
                study_name=self.STUDY,
                location="us-central1",
                confirm_delete=False,
                dry_run=True,
            ),
        )
        client = DeleteClient()
        with self.assertRaisesRegex(ValueError, "confirm-delete"):
            delete_study(
                client=client,
                study_name=self.STUDY,
                location="us-central1",
                confirm_delete=False,
                dry_run=False,
            )
        self.assertEqual(client.deleted, [])
        delete_study(
            client=client,
            study_name=self.STUDY,
            location="us-central1",
            confirm_delete=True,
            dry_run=False,
        )
        self.assertEqual(client.deleted, [self.STUDY])
        with self.assertRaisesRegex(ValueError, "match"):
            delete_study(
                client=None,
                study_name=self.STUDY,
                location="europe-west1",
                confirm_delete=False,
                dry_run=True,
            )

    def test_surrogate_input_validation_is_local(self) -> None:
        rows = [
            {"param.ac_temp": "24", "param.window_size": "5", "metric.cost": "99"},
            {"param.ac_temp": "25", "param.window_size": "6", "metric.cost": "105"},
            {"param.ac_temp": "23", "param.window_size": "4", "metric.cost": "103"},
        ]
        names, features, target = analysis.extract_training_data(rows)
        self.assertEqual(names, ["param.ac_temp", "param.window_size"])
        self.assertEqual(features[0], [24.0, 5.0])
        self.assertEqual(target, [99.0, 105.0, 103.0])
        importance = analysis.fit_random_forest(rows, estimators=5)
        self.assertEqual({item["feature"] for item in importance}, {"ac_temp", "window_size"})
        self.assertAlmostEqual(sum(item["importance"] for item in importance), 1.0)
        with self.assertRaisesRegex(ValueError, "metric.cost"):
            analysis.extract_training_data([{"param.ac_temp": "24"}])


class DeleteClient:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_study(self, *, name: str) -> None:
        self.deleted.append(name)
