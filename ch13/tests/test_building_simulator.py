import unittest

from building_simulator import BuildingEnvironmentSimulator, SimulationInput


class BuildingSimulatorTest(unittest.TestCase):
    def test_seed_makes_cost_reproducible(self) -> None:
        inputs = SimulationInput(24, 10, 5, 50)
        first = BuildingEnvironmentSimulator(seed=42).evaluate(inputs)
        second = BuildingEnvironmentSimulator(seed=42).evaluate(inputs)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first.cost, 30)

    def test_cost_is_floored_at_thirty(self) -> None:
        simulator = BuildingEnvironmentSimulator(outside_temp=0, rng=FixedRng(-1000))
        self.assertEqual(simulator.calculate_cost(30, 100, 0, 0), 30)

    def test_invalid_values_are_rejected(self) -> None:
        simulator = BuildingEnvironmentSimulator(seed=1)
        with self.assertRaisesRegex(ValueError, "insulation_thickness"):
            simulator.calculate_cost(24, -1, 5, 50)
        with self.assertRaisesRegex(ValueError, "finite"):
            simulator.calculate_cost(float("nan"), 1, 1, 1)
        with self.assertRaisesRegex(ValueError, "either seed or rng"):
            BuildingEnvironmentSimulator(seed=1, rng=FixedRng(0))

    def test_comfort_matches_manuscript_formula(self) -> None:
        self.assertEqual(BuildingEnvironmentSimulator.calculate_comfort(24, 5), 110)


class FixedRng:
    def __init__(self, value: float) -> None:
        self.value = value

    def gauss(self, mu: float, sigma: float) -> float:
        return self.value
