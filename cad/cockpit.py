"""Blind glazing pockets machined into the continuous crown, not a cap on top.

4542/4543: the front pair spans most of the brow. One kink leads into the
quarter lights, another to the narrower side lights. Dimensions are an
exterior interpretation of the museum exhibit at 1:144, not production data.
"""

import Part
import numpy as np

from sections import FRAME, V, bezier

# XY outlines on the starboard brow, starting at the inboard sill corner.
# Each quadrilateral is fitted to one plane on the curved skin below.
LIGHTS = (
    # White centre post grows towards the roof (Moscow 2026-03-31 23).
    ((34.15, 1.04), (35.49, 10.19), (44.75, 7.82), (44.10, 2.65)),
    ((35.84, 10.51), (42.25, 15.93), (48.84, 11.45), (45.04, 8.17)),
    ((42.66, 16.21), (51.64, 17.15), (54.15, 12.78), (49.20, 11.82)),
)
FRAME_WIDTH = .36
GLASS_DEPTH = .26


def _unit(v):
    return v * (1. / v.Length)


def _crown(blank, x, y):
    probe = Part.makeLine(V(x, y, 46.), V(x, y, 19.))
    return max(v.Point.z for v in blank.section(probe).Vertexes)


def _rounded(points, trim):
    """Quadratic corners tangent to the four rails, measured in the pane plane."""
    starts, ends = [], []
    for i, p in enumerate(points):
        starts.append(p + trim * _unit(points[i-1] - p))
        ends.append(p + trim * _unit(points[(i+1) % 4] - p))
    edges = []
    for i, p in enumerate(points):
        edges.extend((bezier(starts[i], p, ends[i]), Part.makeLine(ends[i], starts[(i+1) % 4])))
    return Part.Wire(edges)


def _inset(points, sill):
    # Offset two straight edges and intersect them at their true plane bisector.
    corners = []
    for i, p in enumerate(points):
        a = _unit(points[i-1] - p)
        b = _unit(points[(i+1) % 4] - p)
        # The metal sill flares below the front/quarter-light knuckle (4543).
        # Only its bottom edge grows, not the slender posts between windows.
        prev_width = sill if i == 1 else FRAME_WIDTH
        next_width = sill if i == 0 else FRAME_WIDTH
        corners.append(p + (a*next_width + b*prev_width) * (1./a.cross(b).Length))
    return corners


def _pane(blank, footprint, sill):
    corners = np.asarray(footprint)
    heights = [_crown(blank, x, y) for x, y in footprint]
    # A true planar window lets the front panes catch one reflection, unlike
    # projected paint on a doubly curved surface. Set the entire frame below
    # the skin, including the slightly twisted outboard sill corners.
    design = np.column_stack((corners, np.ones(4)))
    dx, dy, h = np.linalg.lstsq(design, heights, rcond=None)[0]
    n = _unit(V(-dx, -dy, 1.))
    h += min(heights - design @ [dx, dy, h]) - .10 / n.z
    points = [V(x, y, dx*x + dy*y + h) for x, y in footprint]
    inner = _inset(points, sill)
    rim_face = Part.Face(_rounded(points, .55))
    glass_face = Part.Face(_rounded([p - GLASS_DEPTH*n for p in inner], .35))
    # Both blind prisms point OUTWARDS. The glazing floor and ring remain
    # integral material; no enclosed void and no thin attached window strips.
    tools = [glass_face.extrude(5.*n)]
    centre = sum(points, V()) * .25
    edges = []
    for i, (p, q) in enumerate(zip(points, points[1:] + points[:1])):
        toward = _unit(n.cross(q-p))
        if (centre-p).dot(toward) < 0:
            toward = -toward
        edges.append((p, toward))
        # Small blind seats follow the metal surround, outside the gasket.
        width = sill if i == 0 else FRAME_WIDTH
        count = max(2, int((q-p).Length/1.55))
        for j in range(count):
            f = .12 + .76*(j+.5)/count
            head = p + f*(q-p) + .53*width*toward - .115*n
            tools.append(Part.makeCylinder(.095, .32, head, n))
    cutter = rim_face.extrude(5.*n).fuse(tools).removeSplitter()
    return cutter, (points[0], n, centre, edges, sill)


def cockpit(blank):
    cutters, panes = [], []
    for footprint, sill in zip(LIGHTS, (.48, .54, .42)):
        for side in (-1, 1):
            tool, pane = _pane(blank, [(x, y*side) for x, y in footprint], sill)
            cutters.append(tool)
            panes.append(pane)
    return cutters, panes


def glazing_color(panes, p):
    for origin, n, centre, edges, sill in panes:
        if (p-centre).Length > 10.5:
            continue
        distance = (p-origin).dot(n)
        on_glass = abs(distance + GLASS_DEPTH) < .012
        if distance < -GLASS_DEPTH-.012 or distance > .012:
            continue
        if all((p-a).dot(to_inside) > -.03 for a, to_inside in edges):
            if on_glass:
                return '#292e36'  # Opaque, near-neutral museum covers, not blue glass.
            if distance < -.012:
                return FRAME  # The inner wall is the gasket, not white porcelain.
            sill_distance = (p - edges[0][0]).dot(edges[0][1])
            return '#697073' if sill_distance < sill - .32 else FRAME
    return None
