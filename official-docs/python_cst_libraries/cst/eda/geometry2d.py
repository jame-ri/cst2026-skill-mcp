# Copyright 1998-2024 Dassault Systemes Deutschland GmbH.

import _cst_eda_interface.geometry2d

# import all classes and functions into namespace "cst.eda.geometry2d"
from _cst_eda_interface.geometry2d import *


def _invoke_transformed(self, geo):
    """
    Copy and transform some geometry object (:py:class:`.R2`, :py:class:`.Segment`, :py:class:`.Curve`, :py:class:`.Shape`).

    :param arg: Input object.
    :return: Transformed copy of the input object.
    """
    if hasattr(geo, "_transformed"):
        return geo._transformed(self)
    else:
        raise TypeError("Object does not support transformations.")

Transformation.apply = _invoke_transformed


def _in_interval(B0, B1, A):
    assert B0<=B1
    return A<=B1 and A>=B0

def _overlapping_intervals(A0,A1, B0,B1):
    return _in_interval(A0, A1, B0) or _in_interval(B0, B1, A0)



class BoundingBox:
    """
    Axis-aligned bounds of a set of points.
    A BoundingBox containing no points is considered empty and tests as ``False``.
    """
    def __init__(self, *args):
        """
        Computes the bounds of a set of points.

        :param args: List of geometry objects. (:py:class:`.R2`, :py:class:`.Segment`, :py:class:`.Curve`, :py:class:`.Shape`, :py:class:`BoundingBox`, ...)
        """
        # Bounds are stored as (xmin, ymin, xmax, ymax), which matches the bounds() method of Shapely objects
        self._bounds = None
        if args:
            self.extend(*args)

    @property
    def bounds(self):
        """
        Bounds as ``(xmin, ymin, xmax, ymax)``, or ``None`` for an empty BoundingBox.
        """
        # Method result is compatible to Shapely: (xmin, ymin, xmax, ymax)
        return self._bounds

    @property
    def xmin(self) -> R2:
        """
        Minimum X extend, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return self._bounds[0]

    @property
    def ymin(self) -> R2:
        """
        Minimum Y extend, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return self._bounds[1]

    @property
    def xmax(self) -> R2:
        """
        Maximum X extend, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return self._bounds[2]

    @property
    def ymax(self) -> R2:
        """
        Maximum Y extend, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return self._bounds[3]

    @property
    def lower_left(self) -> R2:
        """
        ``R2(xmin, ymin)``, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return R2(self._bounds[0], self._bounds[1])

    @property
    def lower_right(self) -> R2:
        """
        ``R2(xmax, ymin)``, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return R2(self._bounds[2], self._bounds[1])

    @property
    def upper_right(self) -> R2:
        """
        ``R2(xmax, ymax)``, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return R2(self._bounds[2], self._bounds[3])

    @property
    def upper_left(self) -> R2:
        """
        ``R2(xmin, ymax)``, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return R2(self._bounds[0], self._bounds[3])

    @property
    def center(self) -> R2:
        """
        Center point, or ``None`` for an empty BoundingBox.
        """
        if self._bounds is None:
            return None
        else:
            return R2((self._bounds[0] + self._bounds[2]) / 2, (self._bounds[1] + self._bounds[3]) / 2)

    def __eq__(self, rhs) -> bool:
        if isinstance(rhs, self.__class__):
            return self.bounds == rhs.bounds
        return NotImplemented

    def __bool__(self):
        """
        ``True`` for non-empty BoundingBox.
        """
        return self._bounds is not None

    def __repr__(self):
        if self._bounds is None:
            return "<Empty BoundingBox>"
        else:
            return "<BoundingBox ({}, {}), ({}, {})>".format(*self._bounds)

    def extend(self, *args):
        """
        Extends the bounds to include a set of points.

        :param args: List of geometry objects. (:py:class:`.R2`, :py:class:`.Segment`, :py:class:`.Curve`, :py:class:`.Shape`, :py:class:`BoundingBox`, ...)
        """
        def add_point(p):
            if self._bounds is None:
                self._bounds = (p.x, p.y, p.x, p.y)
            else:
                self._bounds = (
                    min(self._bounds[0], p.x),
                    min(self._bounds[1], p.y),
                    max(self._bounds[2], p.x),
                    max(self._bounds[3], p.y),
                )

        def add_bounds(b):
            if not b:
                return
            assert len(b) == 4
            if self._bounds is None:
                self._bounds = b
            else:
                self._bounds = (
                    min(self._bounds[0], b[0]),
                    min(self._bounds[1], b[1]),
                    max(self._bounds[2], b[2]),
                    max(self._bounds[3], b[3]),
                )

        for src in args:
            if hasattr(src, "_bounds"):
                add_bounds(src._bounds)
            elif isinstance(src, R2):
                add_point(src)
            elif src:
                # try to cast to R2; works for tuples
                add_point(R2(src))

    def extend_by(self, dist: float):
        """
        Extends all bounds by given distance

        :param dist: distance
        """
        assert dist >= 0.0
        b = self._bounds
        if b is not None:
            self._bounds = ( b[0]-dist, b[1]-dist, b[2]+dist, b[3]+dist )

    def intersects(self, other: "BoundingBox" ):
        """
        Returns whether present and given second bbox intersect.

        :param other: second bbox
        """
        return (self and other and
            _overlapping_intervals(self.xmin, self.xmax, other.xmin, other.xmax) and
            _overlapping_intervals(self.ymin, self.ymax, other.ymin, other.ymax) )
