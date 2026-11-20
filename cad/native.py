"""Native, dependency-free-on-reopen FreeCAD feature trees for the museum kit."""
from pathlib import Path

import FreeCAD as App
import Part
import Sketcher

from sections import frame

V = App.Vector


def _section(doc, key, number, station):
    """Place exact frame geometry on a local YZ sketch: cubic Bézier == clamped cubic B-spline."""
    sketch = doc.addObject('Sketcher::SketchObject', f'{key}Section{number:02d}')
    sketch.Label = f'Шпангоут {number:02d} · X = {station[0]:g} мм'
    sketch.Placement = App.Placement(V(station[0], 0, 0), App.Rotation(V(1, 1, 1), 120))

    def local(p):
        return V(p.y, p.z, 0)

    curves = []
    for edge in frame(station).OrderedEdges:
        if isinstance(edge.Curve, Part.BezierCurve):
            poles = [local(p) for p in edge.Curve.getPoles()]
            if edge.Orientation == 'Reversed':
                poles.reverse()
            curve = Part.BSplineCurve()
            degree = len(poles) - 1
            curve.buildFromPolesMultsKnots(poles, [degree + 1] * 2, [0., 1.], False, degree)
        else:
            curve = Part.LineSegment(local(edge.firstVertex(True).Point), local(edge.lastVertex(True).Point))
        curves.append(curve)
    sketch.addGeometry(curves, False)
    # Dragging a control point must not open a seam in the loft profile.
    n = len(curves)
    sketch.addConstraint([Sketcher.Constraint('Coincident', i, 2, (i+1) % n, 1) for i in range(n)])
    sketch.Visibility = False
    return sketch


def _blank(doc, key, stations):
    first = _section(doc, key, 1, stations[0])
    if len(stations) == 2 and stations[0][1:] == stations[1][1:]:
        obj = doc.addObject('Part::Extrusion', key + 'Blank')
        obj.Label = 'Призматическая обечайка · исходный объём'
        obj.Base = first
        obj.DirMode = 'Custom'
        obj.Dir = V(1, 0, 0)
        obj.LengthFwd = stations[-1][0] - stations[0][0]
    else:
        sketches = [first] + [_section(doc, key, i, s) for i, s in enumerate(stations[1:], 2)]
        obj = doc.addObject('Part::Loft', key + 'Blank')
        obj.Label = 'Наружная обводка · по шпангоутам'
        obj.Sections = sketches
        obj.MaxDegree = 3
        obj.Ruled = False
    obj.Solid = True
    obj.Visibility = False
    return obj


def _union(doc, name, label, shapes):
    obj = doc.addObject('Part::MultiFuse', name)
    obj.Label = label
    obj.Shapes = shapes
    obj.Refine = True
    return obj


def _feature_tree(doc, key, construction):
    stations, operations = construction
    current = _blank(doc, key, stations)
    for i, (kind, label, shapes) in enumerate(operations, 1):
        step = f'{key}Op{i:02d}'
        name = key if i == len(operations) else step
        tools = []
        for j, shape in enumerate(shapes, 1):
            tool = doc.addObject('Part::Feature', f'{step}Tool{j:02d}')
            tool.Label = f'{label} · инструмент {j:02d}'
            tool.Shape = shape
            tool.Visibility = False
            tools.append(tool)
        if kind in ('cut', 'engrave'):
            # A compound of intersecting solids is NOT a valid single Boolean operand.
            cutter = tools[0] if len(tools) == 1 else _union(doc, step + 'Tools', 'Объединение резцов', tools)
            obj = doc.addObject('Part::Cut', name)
            obj.Base = current
            obj.Tool = cutter
            obj.Refine = kind != 'engrave'
            obj.Label = label
        elif kind == 'add':
            obj = _union(doc, name, label, [current, *tools])
        else:
            raise ValueError(f'{key}: неизвестная операция {kind!r}')
        current = obj
    doc.recompute()
    return current


def _bounds(shape):
    b = shape.optimalBoundingBox(False)
    return (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)


def _mismatch(obj, source):
    shape = obj.Shape
    if not obj.isValid() or shape.isNull() or len(shape.Solids) != 1 or not shape.isValid():
        return 'Результат истории не является одним валидным телом.'
    volume = source.Volume
    volume_error = abs(shape.Volume - volume)
    bbox_error = max(abs(a - b) for a, b in zip(_bounds(shape), _bounds(source)))
    if bbox_error <= .005:
        if volume_error <= max(.001, volume * 1.e-7):
            return None
        if volume_error <= volume * 2.e-5:
            # Reparametrizing Bézier sections as sketch splines changes OCC's volume
            # quadrature. Accept that discrepancy only if neither solid adds material.
            limit = max(1.e-7, volume * 1.e-10)
            try:
                for outer, inner in ((shape, source), (source, shape)):
                    residual = outer.cut(inner)
                    if residual.isNull() or not residual.isValid():
                        break
                    if sum(abs(s.Volume) for s in residual.Solids) > limit:
                        break
                else:
                    return None
            except (RuntimeError, ValueError):
                pass  # An inconclusive Boolean is not evidence of equivalence.
    return f'Расхождение: ΔV = {volume_error:.5g} мм³, Δгабарита = {bbox_error:.5g} мм.'


def _property(obj, typ, name, description, value):
    obj.addProperty('App::Property' + typ, name, 'Музейная модель', description)
    setattr(obj, name, value)


def _metadata(obj, part):
    b = part['shape'].optimalBoundingBox(False)
    obj.Label = part['label']
    _property(obj, 'String', 'PartID', 'Ключ детали для атласа и файлов печати', part['id'])
    _property(obj, 'String', 'AssemblyGroup', 'Группа деталей', part['group'])
    _property(obj, 'Vector', 'PrintRotationXYZ', 'Повороты печатной детали по X, Y и Z, градусы', V(*part.get('orientation', (0, 0, 0))))
    _property(obj, 'Vector', 'AssemblySize', 'Габариты в координатах сборки XYZ, мм', V(b.XLength, b.YLength, b.ZLength))
    _property(obj, 'String', 'PrintNote', 'Примечание для печати', part.get('note', ''))
    if 'articulation' in part:
        joint = part['articulation']
        _property(obj, 'Vector', 'HingePivot', 'Точка на оси в координатах сборки, мм', V(*joint['pivot']))
        _property(obj, 'Vector', 'HingeAxis', 'Единичный вектор оси в координатах сборки', V(*joint['axis']))
        _property(obj, 'Angle', 'InspectionAngle', 'Поворот из экспозиционного во второе положение', joint['angle'])


def _appearance(obj, part):
    from presentation import face_palette, srgb

    view = obj.ViewObject
    view.DisplayMode = 'Shaded'
    view.Deviation = .08
    view.AngularDeflection = 12
    view.ShapeColor = srgb(part['color'])
    if part.get('paint'):
        palette = face_palette(obj.Shape, part['paint'], part['color'])
        view.DiffuseColor = [srgb(color) for color in palette]


def save_native(parts, path):
    import FreeCADGui as Gui
    if not App.GuiUp:
        Gui.showMainWindow()
    doc = App.newDocument('BuranVDNKh')
    doc.Label = 'Буран · музейная модель ВДНХ'
    doc.Comment = 'Разъёмная музейная модель. Координаты сборки в мм: X к корме, Y к правому борту, Z вверх.'
    try:
        groups = {}
        finals = []
        for part in parts:
            key, source = part['id'], part['shape']
            if source.isNull() or len(source.Solids) != 1 or not source.isValid():
                raise ValueError(f'{key}: недопустимая исходная BRep-геометрия')
            if part['group'] not in groups:
                group = doc.addObject('App::DocumentObjectGroup', f'Assembly{len(groups) + 1}')
                group.Label = part['group']
                groups[part['group']] = group
            if 'construction' in part:
                obj = _feature_tree(doc, key, part['construction'])
                reason = _mismatch(obj, source)
                if reason:
                    # Retain the full editable history but never silently publish a different shape.
                    history = obj
                    history.Label = 'Редактируемая история · ' + part['label']
                    obj = doc.addObject('Part::Feature', key + 'Exact')
                    obj.Shape = source
                    _property(obj, 'Link', 'ConstructionHistory', 'Дерево сечений и операций', history)
                    _property(obj, 'String', 'GeometryCheck', 'Причина сохранения исходного тела', reason)
                    App.Console.PrintWarning(f'{key}: {reason} Показан точный исходный BRep.\n')
            else:
                obj = doc.addObject('Part::Feature', key)
                obj.Shape = source
            _metadata(obj, part)
            groups[part['group']].addObject(obj)
            finals.append((obj, part))
        doc.recompute()
        final_names = {obj.Name for obj, _ in finals}
        for obj in doc.Objects:
            if 'Shape' in obj.PropertiesList:
                obj.Visibility = obj.Name in final_names
        for obj, part in finals:
            _appearance(obj, part)
        Gui.updateGui()
        view = Gui.activeDocument().activeView()
        view.setAnimationEnabled(False)
        # Camera +Z points to the eye; keep the model upright with global Z up.
        view.setCameraOrientation(App.Rotation(V(), V(0, 0, 1), V(-.72, -1.16, .49), 'ZYX'))
        view.fitAll()
        view.redraw()
        Gui.updateGui()
        doc.saveAs(str(Path(path).resolve()))
    finally:
        App.closeDocument(doc.Name)
