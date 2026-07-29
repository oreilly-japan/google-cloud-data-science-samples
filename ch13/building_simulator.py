"""Deterministic-when-seeded local building HVAC cost simulator.

The cost equation follows the Chapter 13 manuscript.  It deliberately has no
Google Cloud dependency, so it can be used and tested before a cloud run.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Protocol


class NormalRandomSource(Protocol):
    def gauss(self, mu: float, sigma: float) -> float: ...


@dataclass(frozen=True)
class SimulationInput:
    ac_temp: float
    insulation_thickness: float
    window_size: float
    occupancy_density: float


@dataclass(frozen=True)
class SimulationResult:
    cost: float
    comfort: float


def _finite(name: str, value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


class BuildingEnvironmentSimulator:
    """Calculate a noisy monthly HVAC cost for the chapter's virtual building."""

    def __init__(
        self,
        outside_temp: float = 35.0,
        *,
        seed: int | None = None,
        rng: NormalRandomSource | None = None,
    ) -> None:
        if seed is not None and rng is not None:
            raise ValueError("provide either seed or rng, not both")
        self.outside_temp = _finite("outside_temp", outside_temp)
        self._rng: NormalRandomSource = rng if rng is not None else random.Random(seed)

    def calculate_cost(
        self,
        ac_temp: float,
        insulation_thickness: float,
        window_size: float,
        occupancy_density: float,
    ) -> float:
        """Return the manuscript's cost equation, floored at 30 USD."""
        values = SimulationInput(
            ac_temp=_finite("ac_temp", ac_temp),
            insulation_thickness=_finite("insulation_thickness", insulation_thickness),
            window_size=_finite("window_size", window_size),
            occupancy_density=_finite("occupancy_density", occupancy_density),
        )
        if values.insulation_thickness < 0:
            raise ValueError("insulation_thickness must be greater than or equal to 0")
        if values.window_size < 0:
            raise ValueError("window_size must be greater than or equal to 0")
        if values.occupancy_density < 0:
            raise ValueError("occupancy_density must be greater than or equal to 0")

        temp_delta = max(0.0, self.outside_temp - values.ac_temp)
        base_cost = 5.0 * temp_delta**2
        insulation_effect = (
            100.0 / (values.insulation_thickness + 0.1) + 2.0 * values.insulation_thickness
        )
        window_effect = 0.5 * temp_delta * values.window_size**1.5
        occupancy_effect = 10.0 * values.occupancy_density
        noise = self._rng.gauss(0.0, 5.0)
        return max(30.0, base_cost + insulation_effect + window_effect + occupancy_effect + noise)

    @staticmethod
    def calculate_comfort(ac_temp: float, window_size: float) -> float:
        """Return the simple comfort score specified for the multi-objective step."""
        ac_temp = _finite("ac_temp", ac_temp)
        window_size = _finite("window_size", window_size)
        if window_size < 0:
            raise ValueError("window_size must be greater than or equal to 0")
        return 100.0 - abs(ac_temp - 24.0) * 5.0 + window_size * 2.0

    def evaluate(self, values: SimulationInput) -> SimulationResult:
        return SimulationResult(
            cost=self.calculate_cost(**values.__dict__),
            comfort=self.calculate_comfort(values.ac_temp, values.window_size),
        )
