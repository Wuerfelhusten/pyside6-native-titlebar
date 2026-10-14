# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Checks drag-region subtraction against an independent pixel-set oracle.
"""

import pytest

from native_titlebar import geometry


def _pixels(rect: geometry.Rect) -> set[tuple[int, int]]:
    """Returns all integer pixels covered by a half-open rectangle."""
    pixels = set()
    for x in range(rect.x, rect.right):
        for y in range(rect.y, rect.bottom):
            pixels.add((x, y))
    return pixels


@pytest.mark.parametrize(
    "exclusions",
    [
        [],
        [geometry.Rect(4, 2, 5, 4)],
        [geometry.Rect(-2, -2, 6, 7)],
        [geometry.Rect(50, 50, 2, 2)],
        [geometry.Rect(-10, -10, 100, 100)],
        [geometry.Rect(2, 1, 5, 3), geometry.Rect(4, 2, 6, 5)],
        [geometry.Rect(0, 0, 0, 5)],
        [geometry.Rect(0, 0, 20, 8)],
    ],
)
def test_exclusions_leave_exactly_the_available_pixels(
    exclusions: list[geometry.Rect],
) -> None:
    """Checks both pixel coverage and the absence of overlapping regions."""
    bounds = geometry.Rect(0, 0, 20, 8)
    regions = geometry.drag_rectangles(bounds, exclusions)
    expected = _pixels(bounds)
    for exclusion in exclusions:
        expected -= _pixels(exclusion)
    actual: set[tuple[int, int]] = set().union(*(_pixels(r) for r in regions))
    assert actual == expected
    # Equal union and total areas rule out overlaps between returned regions.
    assert sum(r.width * r.height for r in regions) == len(actual)


@pytest.mark.parametrize("scale", [1, 1.25, 1.5, 1.75, 2])
def test_fractional_dpi_excludes_every_part_of_a_widget(scale: float) -> None:
    """Checks outward rounding at common fractional display scales."""
    rect = geometry.physical_rect(3, 5, 17, 23, scale)
    assert rect.x <= 3 * scale < rect.x + 1
    assert rect.y <= 5 * scale < rect.y + 1
    assert rect.right - 1 < 20 * scale <= rect.right
    assert rect.bottom - 1 < 28 * scale <= rect.bottom


def test_no_drag_regions_when_caption_buttons_take_all_available_width() -> (
    None
):
    """Checks that a zero-width title bar has no draggable area."""
    assert not geometry.drag_rectangles(geometry.Rect(0, 0, 0, 32), [])


def test_fractional_zero_size_exclusion_does_not_steal_a_pixel() -> None:
    """Checks that an empty exclusion stays empty after fractional scaling."""
    empty = geometry.physical_rect(0.5, -0.5, 0, 0, 1.25)
    bounds = geometry.Rect(-10, -10, 20, 20)
    assert geometry.drag_rectangles(bounds, [empty]) == [bounds]


@pytest.mark.parametrize("scale", [0, -1, float("inf"), float("nan")])
def test_invalid_scale_fails_before_native_calls(scale: float) -> None:
    """Rejects nonpositive and nonfinite device pixel ratios."""
    with pytest.raises(ValueError, match=r"finite|positive"):
        geometry.physical_rect(0, 0, 20, 30, scale)


def test_negative_dimensions_are_rejected() -> None:
    """Rejects invalid rectangle dimensions in both coordinate systems."""
    with pytest.raises(ValueError, match="dimensions must be nonnegative"):
        geometry.Rect(0, 0, -1, 4)
    with pytest.raises(ValueError, match="Dimensions must be nonnegative"):
        geometry.physical_rect(0, 0, 1, -4, 1)
