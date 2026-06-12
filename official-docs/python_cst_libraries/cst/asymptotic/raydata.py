# Copyright 1998-2024 Dassault Systemes Deutschland GmbH.

#!/usr/bin/env python3
"""Collection of methods to read and manipulate ray data created by the
Asymptotic solver.

Ray data is stored in an `HDF5 <https://www.hdfgroup.org/solutions/hdf5/.>`_
file. A viewer for HDF5 files can be obtained on that website.

To create ray data in the Asymptotic solver, you'll need to activate ray export
(Solver dialog -> Settings... -> Ray storage -> Ray export).

The module provided here takes care of converting the data in the file into
Python data structures.

The documentation given here should also be sufficient to understand the file
format and implement a reader in another programming language.

.. note:: To use this module you will need to install the modules `h5py` (tested
   version: 3.6.0) and `numpy` (tested version: 1.21.4) in your Python
   environment.
"""

import h5py
import numpy as np
import textwrap
from enum import Enum


def read(filename):
    """Read HDF5-file with ray data.

    :return: Instance of ``RayData``"""
    with h5py.File(filename, 'r') as f:
        data = RayData()
        data.version = f.attrs['version']
        data.sources = [RaySource.from_hdf5(src) for name, src in f.items()]
        return data


class RayData:
    """Structure for storing ray data.

    :ivar version: Version of the data format.

    :ivar sources: List of ray path collections, each one represented by a ``RaySource``."""
    version = 1
    sources = []


class RaySource:
    """Represents a source of rays.

    :ivar category: Type of source

    :ivar name: Identifier for this source

    :ivar frequencies: List of frequencies defining the sampling for frequency
        dependent quantities (electric fields, in particular) within this
        ``RaySource``.

    :ivar trees: List of ray trees stored for this source. Each element is a
        ``RaySegment`` representing the root-node of a ray tree.

    """

    category = 0
    name = ""
    frequencies = []
    trees = []

    class _Segments:
        """Buffer for reading the HDF5 data"""

        def __init__(self, _segments):
            segments = _segments[()]  # read entire dataset at once
            self.provenance = segments['provenance']
            self.termination = segments['termination']
            self.hitorder = segments['hitorder']
            self.epsilon = segments['epsilon']
            self.mue = segments['mue']
            self.area1 = segments['area1']
            self.area2 = segments['area2']
            self.position1 = segments['position1']
            self.position2 = segments['position2']
            self.normal1 = segments['normal1']
            self.normal2 = segments['normal2']
            self.efield1 = segments['efield1']
            self.efield2 = segments['efield2']

    @ classmethod
    def from_hdf5(cls, src):
        c = cls()
        a = src.attrs

        val = a['category']
        c.category = val if isinstance(val, str) else val.decode()

        val = a['name']
        c.name = val if isinstance(val, str) else val.decode()

        c.frequencies = np.asarray(src['frequencies'])
        c.trees = []

        # additional sub sources
        c.sources = []

        if 'hierarchy' not in src:
            # no ray data
            return c

        hierarchy = np.array(src['hierarchy'])

        # store data in numpy structures
        segment_data = RaySource._Segments(src['segments'])

        nsegments = len(segment_data.hitorder)
        segments = [RaySegmentProxy.from_hdf5(index, segment_data)
                    for index in range(nsegments)]

        ith = iter(hierarchy)
        while True:
            try:
                c.trees.append(RaySource._build_tree(
                    ith, lambda index: segments[index]))
            except StopIteration:
                break

        return c

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    @classmethod
    def _build_tree(cls, ith, get_segment):
        """Build RayTree for a single path."""
        result = RaySegment(None)
        for segment in result.segments():
            index = next(ith)
            if index >= 0:
                segment.data = get_segment(index)
                segment.reflected = RaySegment(None, segment)
                segment.transmitted = RaySegment(None, segment)

        # Invalidate uninitialized segments
        for segment in result.segments():
            if segment.reflected.data is None:
                segment.reflected = None
            if segment.transmitted.data is None:
                segment.transmitted = None

        return result


class RayTree:
    """Binary tree for representing a ray tree.

    A ray tree consists of several ray segments. Each instance of this class
    represents a segment of the entire ray tree, with reflected and transmitted
    segments branching from it. In effect, the entire ray tree can be reached
    from its root segment. This class provides routines to iterate over all
    segments or all possible paths.

    :example:

    Scenario: Ray segments for a single ray impinging on a dielectric slab,
    maximum number of intersections set to 2:

    .. image:: /_static/images/asymptotic/raystorage-scene.svg
        :scale: 60%
        :alt: Ray segments for a dielectric slab

    In a graph-theoretical sense each segment represents a node in a binary
    tree. The corresponding ``RayTree``-graph for this scenario is illustrated
    in the following image; also indicated is the code to reach the segments
    from ``root``:

    .. image:: /_static/images/asymptotic/raystorage-tree.svg
        :scale: 60%
        :alt: Ray tree for the scenario shown above

    :ivar data: Data stored for this segment.

    :ivar reflected: Reflected segment branching from this segment; ``None`` if
        absent.

    :ivar transmitted: Transmitted segment branching from this segment; ``None``
        if absent.

    :ivar parent: Parent segment of this segment; ``None`` if this is the root
        segment.

    """

    def __init__(self, data, parent=None):
        self.data = data
        self.reflected = None
        self.transmitted = None
        self.parent = parent

    def __repr__(self):
        s = 'data: ' + self.data.__repr__() + '\n'
        s += '- reflected:' + textwrap.indent(self.reflected.__repr__(),
                                              '  ') + '\n'
        s += '- transmitted:' + textwrap.indent(self.transmitted.__repr__(),
                                                '  ')
        return s

    def is_leaf(self):
        """Return True if segment has no child segments."""
        return self.reflected is None and self.transmitted is None

    def segments(self):
        """Iterate over binary tree depth-first, yield segments pre-order.

        The ``reflected`` segments are processed before ``transmitted``
        segments."""
        stack = [self]
        while stack:
            segment = stack.pop()
            if segment is None:
                continue
            yield segment
            stack.append(segment.transmitted)
            stack.append(segment.reflected)

    def paths(self):
        """Iterate over all possible ray paths, yield lists of segments.

        Every possible sequence of segments connecting the root-segment with a
        leaf segment is yielded. The sequences are sorted from root segment
        (first) to leaf segment (last).

        For the example from above, the following 3 ray paths are possible (highlighted in green):

        .. image:: /_static/images/asymptotic/raystorage-scene-path0.svg
            :scale: 25%
            :alt: Path 1

        .. image:: /_static/images/asymptotic/raystorage-scene-path1.svg
            :scale: 25%
            :alt: Path 2

        .. image:: /_static/images/asymptotic/raystorage-scene-path2.svg
            :scale: 25%
            :alt: Path 3

        """
        for segment in self.segments():
            if not segment.is_leaf():
                continue
            result = [segment]
            parent = segment.parent
            while parent is not None:
                result.append(parent)
                parent = parent.parent
            yield list(reversed(result))


class Provenance(Enum):
    """Origin of the RaySegment.

    Possible values: 0 (Incident); 1 (Reflected); 2 (Transmitted).
    """
    Incident = 0
    Reflected = 1
    Transmitted = 2


class Termination(Enum):
    """Termination of RaySegment.

    0 (``No``): Not terminated, ray path continues; 1 (``Exitray``): Ray has arrived at bounding box or at its final destination (e.g. receiver source); 2 (``Deadend``): Solver reached maximum number of intersections for this path."""
    No = 0
    Exitray = 1
    Deadend = 2


class RaySegment(RayTree):
    """Interface to ``RayTree`` and to data stored for each ray segment."""

    def __init__(self, data, parent=None):
        super().__init__(data, parent)

    def provenance(self):
        """Provenance of the segment.

        :return: Value as specified in ``Provenance``"""
        return self.data.provenance()

    def termination(self):
        """Termination behavior of the segment.

        :return: Value as specified in ``Termination``"""
        return self.data.termination()

    def hitorder(self):
        """Number of intersections before this segment."""
        return self.data.hitorder()

    def epsilon(self):
        """Relative electric permittivity in the background medium.

        Assumed to be constant over frequency."""
        return self.data.epsilon()

    def mue(self):
        """Relative magnetic permeability in the background medium.

        Assumed to be constant over frequency."""
        return self.data.mue()

    def area1(self):
        """Ray tube cross section area at start point of segment."""
        return self.data.area1()

    def area2(self):
        """Ray tube cross section area at end point of segment."""
        return self.data.area2()

    def position1(self):
        """Position at start point of segment."""
        return self.data.position1()

    def position2(self):
        """Position at end point of segment."""
        return self.data.position2()

    def normal1(self):
        """Surface normal of intersected geometry at start point of segment."""
        return self.data.normal1()

    def normal2(self):
        """Surface normal of intersected geometry at end point of segment."""
        return self.data.normal2()

    def efield1(self):
        """Complex electric field vectors over frequency at start point of segment."""
        return self.data.efield1()

    def efield2(self):
        """Complex electric field vectors over frequency at end point of segment."""
        return self.data.efield2()

    def areas(self):
        """Ray tube cross section areas at start and end point of segment."""
        return np.asarray([self.area1(), self.area2()])

    def positions(self):
        """Positions at start and end point of segment."""
        return np.asarray([self.position1(), self.position2()])

    def normals(self):
        """Surface normals of intersected geometry at start and end point of segment."""
        return np.asarray([self.normal1(), self.normal2()])

    def efields(self):
        """Complex electric field vectors over frequency at start and end point of segment."""
        return np.asarray([self.efield1(), self.efield2()])

    def length(self):
        """Length of segment."""
        return np.linalg.norm(self.position2() - self.position1())

    def direction(self):
        """Normalized direction of ray."""
        return (self.position2() - self.position1()) / self.length()


class RaySegmentProxy:
    # Implements data interface for RaySegment: Proxy to HDF5-data. Performs data transformation lazily.
    @ classmethod
    def from_hdf5(cls, index, buffer):
        if index < 0:
            return None

        c = cls()
        c.i = index
        c.b = buffer
        return c

    def provenance(self):
        return Provenance(self.b.provenance[self.i])

    def termination(self):
        return Termination(self.b.termination[self.i])

    def hitorder(self):
        return self.b.hitorder[self.i]

    def epsilon(self):
        return self.b.epsilon[self.i]

    def mue(self):
        return self.b.mue[self.i]

    def area1(self):
        return self.b.area1[self.i]

    def area2(self):
        return self.b.area2[self.i]

    def position1(self):
        return np.ndarray(3, buffer=self.b.position1[self.i])

    def position2(self):
        return np.ndarray(3, buffer=self.b.position2[self.i])

    def normal1(self):
        return np.ndarray(3, buffer=self.b.normal1[self.i])

    def normal2(self):
        return np.ndarray(3, buffer=self.b.normal2[self.i])

    def efield1(self):
        nfreq = -1  # determine automatically
        return np.reshape(self.b.efield1[self.i], (nfreq, 3))

    def efield2(self):
        nfreq = -1  # determine automatically
        return np.reshape(self.b.efield2[self.i], (nfreq, 3))


def compute_powerflows(segment):
    """Compute powerflow :math:`P` through the end faces of a ``RaySegment`` according to:

    :math:`P = \\frac{A |\\vec{E}|^2 |\\hat{n}\\cdot\\hat{s}|}{Z_0 \\sqrt{\\mu_{\\text{rel}} \\epsilon_{\\text{rel}}}}`

    where:

    * :math:`A`: Area of ray tube cross section

    * :math:`\\vec{E}`: Complex electric field vector

    * :math:`\\hat{n}`: Normal vector of ray tube cross section surface

    * :math:`\\hat{s}`: Ray direction

    * :math:`Z_0`: Impedance of free space

    * :math:`\\mu_{\\text{rel}}`: Relative magnetic permeability

    * :math:`\\epsilon_{\\text{rel}}`: Relative electric permittivity

    :return: Tuple of powerflow values at start and end point of ray segment

    """
    raydir = segment.direction()

    Z0 = 376.730313668
    impedance = Z0 * np.sqrt(segment.mue() / segment.epsilon())

    powerflows = tuple(segment.areas()[i] / impedance *
                       np.linalg.norm(segment.efields()[i])**2 *
                       np.abs(np.dot(segment.normals()[i], raydir))
                       for i in range(2))

    return powerflows
