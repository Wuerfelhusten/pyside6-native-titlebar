# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Calculates half-open physical-pixel rectangles for native drag regions.
"""

from collections.abc import Iterable
import dataclasses
import math


@dataclasses.dataclass(frozen=True)
class Rect:
    """An immutable rectangle with exclusive right and bottom edges.

    Attributes:
        x: Left coordinate in physical pixels, possibly negative.
        y: Top coordinate in physical pixels, possibly negative.
        width: Nonnegative width in physical pixels.
        height: Nonnegative height in physical pixels.
    """

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        """Rejects negative rectangle dimensions."""
        if self.width < 0 or self.height < 0:
            msg = "Rectangle dimensions must be nonnegative."
            raise ValueError(msg)

    @property
    def right(self) -> int:
        """The exclusive right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """The exclusive bottom edge."""
        return self.y + self.height

    def subtract(self, other: "Rect") -> list["Rect"]:
        """Returns disjoint pieces of this rectangle outside another rectangle.

        Args:
            other: The rectangle to exclude.

        Returns:
            Nonempty rectangles whose union is self minus other.
        """
        if self.width == 0 or self.height == 0:
            return []
        left, top = max(self.x, other.x), max(self.y, other.y)
        right = min(self.right, other.right)
        bottom = min(self.bottom, other.bottom)
        if right <= left or bottom <= top:
            return [self]
        pieces = [
            Rect(self.x, self.y, self.width, top - self.y),
            Rect(self.x, bottom, self.width, self.bottom - bottom),
            Rect(self.x, top, left - self.x, bottom - top),
            Rect(right, top, self.right - right, bottom - top),
        ]
        return [piece for piece in pieces if piece.width and piece.height]


def physical_rect(
    x: float, y: float, width: float, height: float, scale: float
) -> Rect:
    """Rounds a logical exclusion outward to protect fractional-DPI edges.

    Args:
        x: Logical left coordinate.
        y: Logical top coordinate.
        width: Nonnegative logical width.
        height: Nonnegative logical height.
        scale: Finite, positive device pixel ratio.

    Returns:
        The smallest integer rectangle enclosing the scaled input.

    Raises:
        ValueError: If coordinates are nonfinite, dimensions are negative, or
            scale is not positive and finite.
    """
    if not all(math.isfinite(value) for value in (x, y, width, height, scale)):
        msg = "Rectangle coordinates and scale must be finite."
        raise ValueError(msg)
    if width < 0 or height < 0 or scale <= 0:
        msg = "Dimensions must be nonnegative and scale positive."
        raise ValueError(msg)
    left, top = math.floor(x * scale), math.floor(y * scale)
    return Rect(
        left,
        top,
        math.ceil((x + width) * scale) - left if width else 0,
        math.ceil((y + height) * scale) - top if height else 0,
    )


def drag_rectangles(bounds: Rect, exclusions: Iterable[Rect]) -> list[Rect]:
    """Subtracts interactive controls from the available title bar area.

    Args:
        bounds: Available native title bar area, excluding caption controls.
        exclusions: Interactive areas, which may overlap or extend past bounds.

    Returns:
        Disjoint nonempty rectangles that remain draggable.
    """
    regions = [bounds] if bounds.width and bounds.height else []
    for exclusion in exclusions:
        remaining = []
        for region in regions:
            remaining.extend(region.subtract(exclusion))
        regions = remaining
    return regions
