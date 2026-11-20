"""Exterior surface work: paint boundaries, cargo panels and raised museum lettering."""

import math
import os
from pathlib import Path

import FreeCAD as App
import Part

from livery import flag, name_relief
from sections import V, NOSE, box, compound, frame, inset, mid, poly, shell_blank

# Upper boundary of dark nose tiles. The steps and irregular sill are visible on BTS-001.
BELT = [(-2, 24.5), (2.2, 24.5), (6.2, 24.5), (10, 24.5), (10, 22.8),
        (13.2, 21.3), (13.2, 20.1), (16.5, 21.0), (16.5, 20.1), (20, 21.1),
        (20, 20.0), (23.5, 21.0), (23.5, 22.3), (26.7, 21.6), (26.7, 23.2),
        (30.1, 22.4), (30.1, 24.2), (33.4, 23.6), (33.4, 25.1), (36.8, 24.4),
        (36.8, 26.2), (40.2, 25.6), (40.2, 27.4), (44, 26.7), (44, 28.1),
        (46.4, 27.7), (46.4, 7.5), (48.4, 7.5), (48.4, 9.0), (50.5, 9.0),
        (50.5, 6.9), (53.3, 6.9), (53.3, 8.4), (55.8, 8.4), (55.8, 6.5), (72.2, 6.5)]


def belt_z(x):
    for (x0, a), (x1, b) in zip(BELT, BELT[1:]):
        if x0 <= x < x1:
            return a + (b-a)*(x-x0)/(x1-x0)
    return 6.5


def band(points, half_width):
    # Plane strip with mitred corners, extruded across both sides of the hull.
    normals = []
    for (x, z), (u, v) in zip(points, points[1:]):
        length = math.hypot(u-x, v-z)
        normals.append((-(v-z)/length, (u-x)/length))
    outer, inner = [], []
    for i, (x, z) in enumerate(points):
        a, b = normals[max(0, i-1)], normals[min(i, len(normals)-1)]
        f = half_width/(1+a[0]*b[0]+a[1]*b[1])
        dx, dz = f*(a[0]+b[0]), f*(a[1]+b[1])
        outer.append(V(x+dx, -32, z+dz))
        inner.append(V(x-dx, -32, z-dz))
    return Part.Face(poly(outer+list(reversed(inner)))).extrude(V(0, 64, 0))


def ring_y(x, z, r, width=.34):
    axis, origin = V(0, 1, 0), V(x, -28, z)
    return Part.makeCylinder(r, 56, origin, axis).cut(Part.makeCylinder(r-width, 56, origin, axis))


def cap_x(z):
    # On 4541 the lower lip of the cap runs farther aft than the upper lip.
    return 2.64 - .42*(z - 13.2)


def nose_tools():
    tools = [band(BELT, .16), ring_y(52.1, 17.5, 3.0, .35)]
    for x, z, r in [(10.8, 14.7, 1.45), (15.2, 16.3, 1.9), (20.3, 16.5, 1.95),
                    (25.4, 16.7, 1.9), (29.7, 18.5, 1.45), (29.9, 14.8, 1.25)]:
        tools.append(ring_y(x, z, r))
    tools.append(band([(cap_x(z), z) for z in (-2., 32.)], .17))
    for x in (12.5, 58.2):
        tools.append(box(x, -26, -2, .31, 52, 48))
    # Limit cut depth on the changing 3-D contours, including near the round cap.
    limiter = shell_blank([inset(s, .34, .32, .32) for s in NOSE])
    return [compound(tools).cut(limiter)]


def side_panel(x, z, w, h, side, width=.30):
    # The flush inspection covers in frame 4537 have eased or fully oblong ends.
    def contour(offset, radius):
        x0, x1 = x+offset, x+w-offset
        z0, z1 = z+offset, z+h-offset
        r = radius
        k = 2**-.5
        def v(u, h0):
            return V(u, side*20.45, h0)
        a, b, c, d = v(x0+r,z0), v(x1-r,z0), v(x1,z0+r), v(x1,z1-r)
        e, f, g, j = v(x1-r,z1), v(x0+r,z1), v(x0,z1-r), v(x0,z0+r)
        return Part.Wire([Part.makeLine(a,b), Part.Arc(b,v(x1-r+r*k,z0+r-r*k),c).toShape(),
                          Part.makeLine(c,d), Part.Arc(d,v(x1-r+r*k,z1-r+r*k),e).toShape(),
                          Part.makeLine(e,f), Part.Arc(f,v(x0+r-r*k,z1-r+r*k),g).toShape(),
                          Part.makeLine(g,j), Part.Arc(j,v(x0+r-r*k,z0+r-r*k),a).toShape()])
    radius = min(1.35,.40*h,.40*w)
    outer = Part.Face(contour(0,radius))
    inner = Part.Face(contour(width,radius-width))
    return outer.cut(inner).extrude(V(0,-side*.72,0))


def panel_tools(x0, x1):
    tools = []
    start, end = max(x0, 72), min(x1, 204)
    if end > start:
        tools.append(box(start-.01, -.26, 39.55, end-start+.02, .52, 2))
        for side in (-1, 1):
            y = 19.63 if side > 0 else -20.8
            tools.append(box(start, y, 25.55, end-start, 1.17, .42))
    for x in (76.7, 98.8, 121.5, 145, 180.8, 201.6, 225.5):
        if not x0+.6 < x < x1-.6:
            continue
        inner = Part.Face(frame(inset(mid(x-.1), .34, .32, .35))).extrude(V(.7, 0, 0))
        tools.append(box(x, -24, 26.7, .36, 48, 15).cut(inner))
    # Paired shallow fastener seats below the split lines of the visible side panels.
    # Only the large fittings are represented at 1:144; no indiscriminate rivet grid.
    for x in (82.4, 100.5, 123.2, 146.6, 161.7, 188.0, 202.8):
        if not x0+.6 < x < x1-.6:
            continue
        for side in (-1, 1):
            for offset in (0, .95):
                centre = V(x+offset,side*20.12,24.52)
                tools.append(Part.makeCylinder(.225, .34, centre, V(0,-side,0)))
    for x, z, w, h in [(79, 12.6, 8.6, 7.2), (104.2, 14.4, 6.0, 3.3),
                       (127.7, 15, 10.2, 6.3), (149, 18, 4.4, 2.8), (174.4, 14.3, 3.8, 1.55),
                       (183.4, 15.5, 4.8, 1.8), (199.4, 16.8, 4.1, 1.75), (211.8, 12, 7.2, 6.7)]:
        if x0 < x and x+w < x1:
            tools.extend(side_panel(x, z, w, h, s) for s in (-1, 1))
    # Selected belly tile courses: shallow staggered lines rather than separate loose tiles.
    for i, y in enumerate((-6.4, -2.15, 2.10)):
        tools.append(box(x0-.1, y, -.3, x1-x0+.2, .30, .55))
        for x in range(int(x0+5+i%2*3), int(x1-1), 8):
            tools.append(box(x, y+.3, -.3, .30, 3.95, .55))
    return tools


def hinges(x0, x1):
    shapes = []
    for x in range(79, 199, 9):
        if not x0 < x < x1-3:
            continue
        for s in (-1, 1):
            y = 19.80 if s>0 else -20.15
            shapes.append(box(x-.16, y, 25.96, 2.88, .35, 1.04))
            for dx in (0, 1.42):
                shapes.append(Part.makeCylinder(.415, 1.1, V(x+dx,s*20.04,26.54), V(1,0,0)))
    return shapes


def lettering(text, size, x0, z0, side, width=None):
    paths = [os.environ.get('BURAN_FONT', ''),
             '/System/Library/Fonts/Supplemental/Arial Narrow Bold Italic.ttf',
             '/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf',
             'C:/Windows/Fonts/arialbi.ttf']
    font = next((p for p in paths if p and Path(p).is_file()), None)
    if not font:
        raise FileNotFoundError('Set BURAN_FONT to a Cyrillic bold italic TrueType font')
    glyphs = Part.makeWireString(text, font, size)
    faces = [Part.makeFace(w, 'Part::FaceMakerBullseye') for w in glyphs if w]
    bb = compound(faces).BoundBox
    # Local glyph X follows screen-right on each side: never mirror the word itself.
    start = x0 if side < 0 else x0+(width or bb.XLength)
    stretch = (width or bb.XLength)/bb.XLength
    out = []
    for face in faces:
        face = face.copy()
        face.translate(V(-bb.XMin, -bb.YMin, 0))
        if abs(stretch-1) > .001:
            m = App.Matrix()
            m.A11 = stretch
            face = face.transformGeometry(m)
        face.rotate(V(), V(1, 0, 0), 90)
        if side > 0:
            face.rotate(V(), V(0, 0, 1), 180)
        face.translate(V(start, side*19.84, z0))
        out.append(face.extrude(V(0, side*.46, 0)))
    return out


def markings():
    shapes = []
    for s in (-1, 1):
        shapes.extend(name_relief(s))
        shapes.extend(lettering('СССР', 1.90, 190.2, 18.22, s, 6.8))
        shapes.append(flag(s))
    return shapes
