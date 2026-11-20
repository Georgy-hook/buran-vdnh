"""Blind, fanned courses below the Moscow exhibit's removable cheek panels.

The last section inherits the developed arc, joint phase and land colours of
Bay. Ahead of it the same tracks converge around the *actual* rounded loft.
Course count is a resin-scale interpretation, not a flight tile identification.
"""
from bisect import bisect_right
from functools import lru_cache
import math

import Part

from belly import COURSE, DEPTH, MOUTH, PITCH, TILE_FINISHES
from sections import TILES, V, compound, poly

START = 7.86                       # Leave the smooth cap and collar alone.
JOINT = 72.


class Frame:
    """One starboard half-section, from keel centre around the lower chine."""

    def __init__(self, contour):
        self.contour = contour
        self.arc = [0.]
        self.diagonal = [y + z for y, z in contour]
        for (a, b), (y, z) in zip(contour, contour[1:]):
            self.arc.append(self.arc[-1] + math.hypot(y - a, z - b))

    def segment(self, index):
        a, b = self.contour[index]
        y, z = self.contour[index + 1]
        length = self.arc[index + 1] - self.arc[index]
        return a, b, (y - a) / length, (z - b) / length

    def point(self, x, u, depth):
        # u is signed developed distance from keel centre; positive depth
        # enters the material. The normal is continuous at the keel flat.
        distance = abs(u)
        i = min(len(self.arc) - 2, max(0, bisect_right(self.arc, distance) - 1))
        a, b, dy, dz = self.segment(i)
        t = distance - self.arc[i]
        return V(x, math.copysign(a + t*dy - depth*dz, u), b + t*dz + depth*dy)

    def locate(self, y, z):
        # Inverse map also returns the real depth, so the pale wash belongs
        # to the floors of the BRep cuts, not lines drawn on the tile lands.
        w = abs(y)
        i = min(len(self.arc) - 2, max(0, bisect_right(self.diagonal, w + z) - 1))
        a, b, dy, dz = self.segment(i)
        distance = self.arc[i] + (w - a)*dy + (z - b)*dz
        depth = (z - b)*dy - (w - a)*dz
        return math.copysign(distance / self.arc[-1], y), depth


class DevelopedBelly:
    def __init__(self, blank):
        # sections.frame starts with the keel flat, then the starboard chine.
        # Sampling that very face avoids station-interpolation offsets at the
        # rapidly widening front. At X72 it is the same cubic as the bay.
        face = blank.Faces[1]
        self.chine = face.Surface
        self.u0, self.u1, self.v0, self.v1 = face.ParameterRange
        self.at = lru_cache(maxsize=1024)(self.frame)
        self.count = round(2 * self.at(JOINT).arc[-1] / COURSE)

    def frame(self, x):
        lo, hi = self.v0, self.v1
        for _ in range(31):
            v = .5 * (lo + hi)
            if self.chine.value(self.u0, v).x < min(x, JOINT):
                lo = v
            else:
                hi = v
        points = [self.chine.value(self.u0 + (self.u1-self.u0)*i/64, v)
                  for i in range(65)]
        return Frame([(0., points[0].z)] + [(p.y, p.z) for p in points])

    def paint(self, x, y, z):
        if not START <= x <= JOINT or z > 10.:
            return TILES
        # Interpolate two cached samples. A paint query is made for every
        # tessellated face; the cached frames contain only numeric values.
        key = math.floor(x * 2) * .5
        t = (x - key) * 2
        u, h = self.at(key).locate(y, z)
        v, k = self.at(key + .5).locate(y, z)
        across, depth = u*(1-t) + v*t, h*(1-t) + k*t
        if abs(across) > 1.003 or not -.05 < depth < .32:
            return TILES
        if depth > .107:
            if abs(y) < 9.4:
                return '#5a605f'
            return '#626766' if abs(y) < 16.2 else '#656967'
        row = math.floor((across + 1.) * self.count / 2)
        column = math.floor(x/PITCH - (row % 2)*.5)
        return TILE_FINISHES[(column*31 + row*13 + (column*row) % 17) % len(TILE_FINISHES)]

    def rail_wire(self, x, j):
        frame = self.at(x)
        u = frame.arc[-1] * (2*j/self.count - 1)
        rim = [(-.12, -.28), (-.092, .035), (-.036, .222),
               (.036, .222), (.092, .035), (.12, -.28)]
        return poly([frame.point(x, u + width, depth) for width, depth in rim])

    def cuts(self):
        # A ruled loft following several skin frames gives curved tracks.
        # Continue them past the real joint plane: there is no smooth band
        # immediately forward of X72. No blades extend onto the cheek lids.
        stations = [START, 9.55, 12.65, 16.25, 21.15, 27.65, 34.25,
                    42.35, 49.45, 55.65, 62.35, 68.65, JOINT + .22]
        rails = [Part.makeLoft([self.rail_wire(x, j) for x in stations], True, True)
                 for j in range(1, self.count)]
        cross = []
        for j in range(self.count):
            phase = (j % 2) * PITCH / 2
            for i in range(math.ceil((START - phase)/PITCH), math.ceil((JOINT - phase)/PITCH)):
                x = i*PITCH + phase
                if x < START + .16 or x > JOINT - .20:
                    continue
                # At the nose drain, a 12.60 centre would put the rear wall
                # exactly tangent to the 2.4 radius hole (x=12.70 at y=0).
                # Pull back that one short joint, leaving a printable land.
                if j == self.count // 2 and abs(x - 12.60) < .001:
                    x -= .24
                frame = self.at(x)
                us = [frame.arc[-1] * (2*(j + k/4)/self.count - 1) for k in range(5)]
                rim = [(u, DEPTH) for u in us] + [(u, -.24) for u in reversed(us)]
                wire = poly([frame.point(x - MOUTH/2, u, depth) for u, depth in rim])
                cross.append(Part.Face(wire).extrude(V(MOUTH, 0, 0)))
        return compound(rails), compound(cross)
