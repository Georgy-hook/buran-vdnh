"""Two presentations of the exact assembled BReps. No STL round trip or external assets."""
from array import array
from collections import Counter
from functools import lru_cache
import json
import math
import struct
import sys

import FreeCAD as App
import MeshPart

from native import save_native

__all__ = ['make_glb', 'save_native']


@lru_cache(maxsize=256)
def srgb(hex_color):
    s = hex_color.removeprefix('#')
    if len(s) != 6:
        raise ValueError(f'Expected #rrggbb, got {hex_color!r}')
    return tuple(int(s[i:i+2], 16) / 255. for i in (0, 2, 4))


def _linear(channel):
    return channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055)**2.4


def finish(color):
    """Metalness/roughness of the *miniature's finish*, not flight specifications."""
    if color in ('#263c4c', '#1d333e', '#243943'):
        return .04, .17  # deep, reflective glazing; not a transparent hollow body
    if color in ('#626b70', '#a4aeac', '#828c89', '#606769'):
        return .50, .46  # metal surrounds, oleos and gear hardware
    if color in ('#232a2b', '#343b3e', '#2c3033', '#43484c', '#292d30',
                 '#323539', '#32383d', '#475057', '#383b3c'):
        return .0, .88  # tyre rubber and dark external thermal surfaces
    if color in ('#242f34', '#37474e', '#49595e'):
        return .17, .68  # coated display plinth
    if color in ('#f1dfba', '#bb805b'):
        return .30, .47  # the plinth's embossed legend
    return .0, .59  # satin-painted museum airframe, insignia and access covers


def _segments(shape):
    # Tessellate the whole solid: trimming wires and edges are shared, including at seams.
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.045,
                                  AngularDeflection=.20, Relative=False, Segments=True)
    vertices, triangles = mesh.Topology
    faces = shape.Faces
    if len(faces) != mesh.countSegments():
        raise ValueError('CAD tessellator returned a different number of face segments')
    for i, face in enumerate(faces):
        yield face, vertices, [triangles[t] for t in mesh.getSegment(i)]


def face_palette(shape, paint, base):
    """FreeCAD displays one color per BRep face; vote by area, not by UV midpoint.

    A centroid of a trimmed face could be off the surface or inside a hole (lettering).
    Triangle interiors produce surface samples even for concave faces and thin strokes.
    """
    colors = []
    for _, vertices, triangles in _segments(shape):
        weights = Counter()
        for i, j, k in triangles:
            a, b, c = vertices[i], vertices[j], vertices[k]
            p = (a + b + c) / 3
            weights[paint(p.x, p.y, p.z)] += (b - a).cross(c - a).Length
        colors.append(weights.most_common(1)[0][0] if weights else base)
    return colors


def _norm(v):
    length = v.Length
    return v / length if length > 1.e-12 else v


class _Primitive:
    """Indexed interleaved float32 positions/normals, packed as consumed by WebGL."""

    def __init__(self):
        self.data = bytearray()
        self.indices = array('I')
        self.unique = {}
        self.lo = [math.inf] * 3
        self.hi = [-math.inf] * 3

    def add(self, vertex):
        p, n = vertex
        # CAD mm (aft, starboard, up) -> right-handed glTF m (aft, up, port).
        key = struct.pack('<6f', p.x*.001, p.z*.001, -p.y*.001, n.x, n.z, -n.y)
        i = self.unique.get(key)
        if i is None:
            i = self.unique[key] = len(self.unique)
            self.data.extend(key)
            for axis, value in enumerate(struct.unpack_from('<3f', key)):
                self.lo[axis] = min(self.lo[axis], value)
                self.hi[axis] = max(self.hi[axis], value)
        self.indices.append(i)

    def finish(self, glb, mat):
        count = len(self.unique)
        view = glb.view(self.data, 34962, byteStride=24)
        pos = glb.accessor(view, 5126, count, 'VEC3', min=self.lo, max=self.hi)
        norm = glb.accessor(view, 5126, count, 'VEC3', byteOffset=12)
        small = count <= 65535  # maximum index value is reserved by glTF
        indices = array('H', self.indices) if small else self.indices
        if sys.byteorder != 'little':
            indices.byteswap()
        iv = glb.view(indices.tobytes(), 34963)
        ix = glb.accessor(iv, 5123 if small else 5125, len(indices), 'SCALAR')
        return dict(attributes={'POSITION': pos, 'NORMAL': norm}, indices=ix, material=mat, mode=4)


class _Document:
    def __init__(self):
        self.binary = bytearray()
        self.palette = {}
        self.doc = dict(asset={'version': '2.0', 'generator': 'Buran / FreeCAD BRep atelier'},
                        scene=0, scenes=[{'nodes': []}], nodes=[], meshes=[], materials=[],
                        bufferViews=[], accessors=[])

    def view(self, data, target, **params):
        self.binary.extend(b'\0' * (-len(self.binary) % 4))
        views = self.doc['bufferViews']
        views.append(dict(buffer=0, byteOffset=len(self.binary), byteLength=len(data), target=target, **params))
        self.binary.extend(data)
        return len(views) - 1

    def accessor(self, view, component, count, kind, **params):
        items = self.doc['accessors']
        items.append(dict(bufferView=view, componentType=component, count=count, type=kind, **params))
        return len(items) - 1

    def material(self, color):
        if color not in self.palette:
            materials = self.doc['materials']
            self.palette[color] = len(materials)
            metalness, roughness = finish(color.lower())
            materials.append(dict(name=color, pbrMetallicRoughness={
                'baseColorFactor': [*map(_linear, srgb(color)), 1.],
                'metallicFactor': metalness, 'roughnessFactor': roughness,
            }))
        return self.palette[color]

    def append_part(self, part, buckets):
        node = len(self.doc['nodes'])
        primitives = [b.finish(self, self.material(color)) for color, b in buckets.items()]
        if not primitives:
            raise ValueError(f"Empty mesh for {part['id']}")
        self.doc['meshes'].append(dict(name=part['label'], primitives=primitives))
        self.doc['nodes'].append(dict(name=part['id'], mesh=node))
        self.doc['scenes'][0]['nodes'].append(node)

    def bytes(self):
        self.doc['buffers'] = [dict(byteLength=len(self.binary))]
        meta = json.dumps(self.doc, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        meta += b' ' * (-len(meta) % 4)
        self.binary.extend(b'\0' * (-len(self.binary) % 4))
        return b''.join([struct.pack('<4sIIII', b'glTF', 2, 28 + len(meta) + len(self.binary), len(meta), 0x4e4f534a),
                         meta, struct.pack('<II', len(self.binary), 0x004e4942), self.binary])


def _buckets(part):
    buckets = {}
    paint = part.get('paint')
    color_at = lru_cache(maxsize=65536)(paint) if paint else None

    def emit(color, a, b, c):
        bucket = buckets.get(color)
        if bucket is None:
            bucket = buckets[color] = _Primitive()
        for v in (a, b, c):
            bucket.add(v)

    def painted(a, b, c):
        # Bisect the LONGEST edge, not all four subtriangles: cuts in long, thin CAD
        # faces otherwise grow exponentially. Sample triangle interiors, not boundary
        # vertices belonging to adjacent materials. Reuse normals on the original facet.
        ab, bc, ca = ((a[0]-b[0]).Length, (b[0]-c[0]).Length, (c[0]-a[0]).Length)
        longest = max(ab, bc, ca)
        if longest == bc:
            a, b, c = b, c, a
        elif longest == ca:
            a, b, c = c, a, b
        p, q, r = a[0], b[0], c[0]
        center = (p + q + r) / 3
        mid_color = color_at(*center)
        uniform = longest <= .25
        if not uniform:
            uniform = all(color_at(*(v*.99 + center*.01)) == mid_color for v in (p, q, r))
            if uniform and longest > .85:
                # A long box face may have an entire narrow stripe BETWEEN the four
                # samples above. Probe rows at submillimetre pitch but emit ONE triangle
                # if it is uniform. Number of rows depends on altitude, not edge length:
                # probing long sliver triangles costs O(length), not O(length²).
                pq, pr = q-p, r-p
                rows = max(1, math.ceil(pr.cross(pq).Length / (longest*.72)))
                for row in range(rows):
                    t = (row+.5) / rows
                    start = p + pr*t
                    step = pq*(1.-t)
                    cols = max(1, math.ceil(longest*(1.-t) / .72))
                    if any(color_at(*(start + step*((col+.5)/cols))) != mid_color for col in range(cols)):
                        uniform = False
                        break
        if uniform:
            emit(mid_color, a, b, c)
            return
        midpoint = ((p+q)*.5, _norm(a[1]+b[1]))
        painted(a, midpoint, c)
        painted(midpoint, b, c)

    for face, vertices, triangles in _segments(part['shape']):
        surface = face.Surface
        planar = surface.TypeId == 'Part::GeomPlane'
        normal_cache = {}
        for tri in triangles:
            pts = [vertices[i] for i in tri]
            facet = (pts[1]-pts[0]).cross(pts[2]-pts[0])
            if facet.Length < 1.e-11:
                continue
            facet = _norm(facet)
            verts = []
            for i, pt in zip(tri, pts):
                if not planar and i not in normal_cache:
                    # Trimmed face orientation (including mirrored solids) is handled by
                    # normalAt. At a pole an analytic normal may be undefined: use facet.
                    try:
                        normal_cache[i] = _norm(face.normalAt(*surface.parameter(pt)))
                    except (ValueError, RuntimeError, ArithmeticError):
                        normal_cache[i] = None
                n = normal_cache.get(i)
                verts.append((pt, n if n is not None and n.dot(facet) > .05 else facet))
            if paint:
                painted(*verts)
            else:
                emit(part['color'], *verts)
    return buckets


def make_glb(parts):
    """Return a complete GLB; identity transforms and exact IDs allow independent explosion."""
    document = _Document()
    for part in parts:
        document.append_part(part, _buckets(part))
    return document.bytes()
