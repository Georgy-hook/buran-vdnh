"""Orient, export and *re-read* each binary STL. All dimensions are millimetres."""

import math
from pathlib import Path
import struct

import FreeCAD as App
import MeshPart
import numpy as np
import Part

from sections import V

VOLUME = np.array([153.4, 87.0, 165.0])
# 3 mm raft clearance on each side, 6 mm lift and 3 mm overhead.
ALLOWANCE = np.array([6.0, 6.0, 9.0])


def rounded(values):
    return [round(float(v), 3) for v in values]


def dims(bounds):
    return rounded([bounds.XLength, bounds.YLength, bounds.ZLength])


def pose(angles):
    rotation = App.Rotation()
    for axis, angle in zip([V(1,0,0), V(0,1,0), V(0,0,1)], angles):
        rotation = App.Rotation(axis, angle).multiply(rotation)
    return rotation.toMatrix()


def inspect_stl(path):
    raw = Path(path).read_bytes()
    count, = struct.unpack_from('<I', raw, 80)
    if not count or len(raw) != 84+count*50:
        raise ValueError(f'{path.name}: broken binary STL')
    fmt = np.dtype([('normal','<f4',(3,)), ('p','<f4',(3,3)), ('attr','<u2')])
    facets = np.frombuffer(raw, fmt, count, offset=84)
    tri = facets['p'].astype('float64')
    if not np.isfinite(tri).all():
        raise ValueError(f'{path.name}: non-finite vertex')
    vertices, ids = np.unique(tri.reshape(-1,3), axis=0, return_inverse=True)
    faces = ids.reshape(-1,3)
    edges = np.concatenate([faces[:,[0,1]], faces[:,[1,2]], faces[:,[2,0]]])
    unique, edge_ids, counts = np.unique(np.sort(edges,axis=1), axis=0,
                                          return_counts=True, return_inverse=True)
    bad = np.count_nonzero(counts != 2)
    balance = np.bincount(edge_ids.reshape(-1), weights=np.sign(edges[:,1]-edges[:,0]))
    bad_winding = np.count_nonzero(balance)
    doubled_area = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    degenerate = np.count_nonzero(np.linalg.norm(doubled_area, axis=1) < 1.e-10)
    if bad or bad_winding or degenerate:
        raise ValueError(f'{path.name}: {bad} non-manifold edges; {bad_winding} unbalanced; {degenerate} degenerate faces')

    # Connect components by common vertices after proving every edge is 2-valent.
    roots = list(range(len(vertices)))
    def root(i):
        while roots[i] != i:
            roots[i] = roots[roots[i]]
            i = roots[i]
        return i
    for a,b in unique.tolist():
        roots[root(a)] = root(b)
    components = len({root(i) for i in range(len(roots))})
    signed_volume = float(np.einsum('ij,ij->',tri[:,0],doubled_area)/6)
    if components != 1 or signed_volume <= 0:
        raise ValueError(f'{path.name}: {components} shells or inward normals ({signed_volume})')
    minimum, maximum = vertices.min(axis=0), vertices.max(axis=0)
    size = maximum-minimum
    if np.max(np.abs(minimum)) > .002 or np.any(size+ALLOWANCE > VOLUME):
        raise ValueError(f'{path.name}: origin {minimum} / envelope {size} plus raft allowance exceed budget')
    return dict(facets=int(count), printSize=rounded(size), meshVolumeMM3=round(signed_volume,3),
                freeWithAllowance=rounded(VOLUME-size-ALLOWANCE), closedComponents=components,
                nonManifoldEdges=int(bad), inconsistentEdges=int(bad_winding))


def export(part, directory):
    shape = part['shape']
    if len(shape.Solids) != 1 or not shape.isValid() or shape.Volume <= 0 or len(shape.Shells) != 1:
        raise ValueError(part['id']+': must be one CAD solid without a sealed cavity')
    path = directory / (part['id']+'.stl')
    errors = []
    trials = [(0.035,.18), (.026,.14), (.048,.22)]
    for lin, ang in trials:
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=lin, AngularDeflection=ang, Relative=False)
        mesh.transform(pose(part['orientation']))
        bb = mesh.BoundBox
        mesh.translate(-bb.XMin,-bb.YMin,-bb.ZMin)
        mesh.write(str(path))
        try:
            result = inspect_stl(path)
            break
        except ValueError as exc:
            errors.append(f'{lin}/{ang}: {exc}')
    else:
        raise ValueError('; '.join(errors))
    if abs(result['meshVolumeMM3']/shape.Volume-1.0) > .009:
        raise ValueError(part['id']+': CAD and printed STL volumes differ by over 0.9%')
    return dict(id=part['id'], label=part['label'], group=part.get('group','Калибры'),
                size=dims(shape.optimalBoundingBox(False)), stl='files/stl/'+path.name,
                orientation=list(part['orientation']), linearDeflection=lin,
                angularDeflectionRad=ang, cadVolumeMM3=round(shape.Volume,3), **result)


JOINTS = set(frozenset(i.split('/')) for i in [
    'Nose/Bay','Bay/Aft','Aft/Stern','Stern/LowerFlap','Bay/WingPort','Bay/WingStarboard',
    'Aft/WingPort','Aft/WingStarboard','Aft/Fin','Nose/GearFront','Aft/BogiePort','Aft/BogieStarboard',
    'GearFront/Plinth','BogiePort/Plinth','BogieStarboard/Plinth',
    'Bay/BayDoorPort','Bay/BayDoorStarboard','Aft/BayDoorPort','Aft/BayDoorStarboard',
    'Fin/BrakePortLower','Fin/BrakePortUpper','Fin/BrakeStarboardLower','Fin/BrakeStarboardUpper',
])


# All coincident points along a finely engraved seam are equally near. Asking
# FreeCAD to enumerate the edge/face IDs of every solution is quadratic. A
# point on both actual solids proves seating by the triangle inequality; if
# a feature moves, fall back to the full minimum-distance calculation.
_SEATS = {
    frozenset(('Nose', 'Bay')): (72., 1.4, 1.62),
    frozenset(('Bay', 'Aft')): (160., 1.4, 1.62),
    frozenset(('Aft', 'Stern')): (232., 1.4, 1.62),
    frozenset(('Stern', 'LowerFlap')): (235.2, .7, 3.8),
    frozenset(('Aft', 'Fin')): (214., 1.2, 40.),
    frozenset(('Nose', 'GearFront')): (57.3, .58, 5.8),
}
for _hand, _side in [('Port', -1), ('Starboard', 1)]:
    _SEATS[frozenset(('Bay', 'Wing'+_hand))] = (128.1, 20.*_side, 7.12)
    _SEATS[frozenset(('Aft', 'Wing'+_hand))] = (164.2, 20.*_side, 7.12)
    _SEATS[frozenset(('Aft', 'Bogie'+_hand))] = (174.4, 12.7*_side, 5.8)
    _SEATS[frozenset(('Bay', 'BayDoor'+_hand))] = (76.9, 1.2*_side, 37.9)
    _SEATS[frozenset(('Aft', 'BayDoor'+_hand))] = (186.3, 1.2*_side, 37.9)


def seating_distance(a, b, ids):
    if ids in _SEATS:
        witness = Part.Vertex(V(*_SEATS[ids]))
        upper_bound = witness.distToShape(a)[0] + witness.distToShape(b)[0]
        if upper_bound <= .00001:
            return upper_bound
    return a.distToShape(b)[0]


def assembly_check(parts):
    by_id = {p['id']: p['shape'] for p in parts}
    all_bb, ship_bb = App.BoundBox(), App.BoundBox()
    measured = []
    matched = set()
    collisions = []
    for i,p in enumerate(parts):
        print(f"Контакты: {p['id']}", flush=True)
        a = p['shape']
        # A loose extrema box is fine for culling collision pairs, but it
        # includes unused spline poles above the fin. Quote physical extents.
        exact_bounds = a.optimalBoundingBox(False)
        all_bb.add(exact_bounds)
        if p['group'] != 'Шасси и стенд':
            ship_bb.add(exact_bounds)
        for q in parts[i+1:]:
            b = q['shape']
            name = f"{p['id']}/{q['id']}"
            required = frozenset((p['id'],q['id']))
            overlap = a.common(b).Volume if a.BoundBox.intersect(b.BoundBox) else 0.
            measured.append(abs(overlap))
            if abs(overlap) > .002:
                collisions.append(f'{name} = {overlap:.4f} mm³')
            if required in JOINTS:
                distance = seating_distance(a, b, required)
                if distance > .002:
                    collisions.append(f'{name} seating gap {distance:.4f} mm')
                matched.add(required)
    if collisions or matched != JOINTS:
        raise ValueError('Assembly: '+', '.join(collisions)+f' missing {JOINTS - matched}')
    # Centre of the aircraft alone must project inside the three tyre contact pads.
    moving = [p['shape'].Solids[0] for p in parts if p['id'] != 'Plinth']
    mass = sum(s.Volume for s in moving)
    centre = sum((s.CenterOfMass*s.Volume for s in moving), V())*(1/mass)
    triangle = [(54,0),(169,-22),(169,22)]
    margins = []
    for (x,y),(u,v) in zip(triangle,triangle[1:]+triangle[:1]):
        margins.append(((u-x)*(centre.y-y)-(v-y)*(centre.x-x))/math.hypot(u-x,v-y))
    if min(margins) < 1:
        raise ValueError('Centre of mass is outside wheel support polygon')
    return dict(dimensions=dims(all_bb), orbiter=dims(ship_bb), checkedPairs=len(measured),
                seatingInterfaces=len(matched), maxOverlapMM3=round(max(measured),7),
                aircraftCOMmm=rounded(centre), wheelTriangleMarginMM=round(min(margins),2),
                solidResinML=round(sum(s.Volume for s in by_id.values())/1000,1))
