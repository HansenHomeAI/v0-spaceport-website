from __future__ import annotations

from typing import List, Protocol, Tuple

LatLon = Tuple[float, float]


class ElevationProvider(Protocol):
    """Protocol for sampling elevations along a path."""

    def sample(self, points: List[LatLon]) -> List[float]:
        """Return elevations in meters above mean sea level for each point."""

    def max_batch_size(self) -> int:
        """Return the maximum number of points that can be fetched in a single request."""
