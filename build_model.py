#!/usr/bin/env python3
"""Regenerate native CAD, print pack and offline viewer data with FreeCAD 1.1.

On macOS with the official FreeCAD.app distribution:
    F=/Applications/FreeCAD.app/Contents/Resources
    PYTHONPATH="$F/lib" "$F/bin/python" build_model.py
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'cad'))


def build():
    import FreeCAD as App
    from calibration import build as gauges
    import display
    import hull
    import lifting
    from presentation import make_glb, save_native
    from printing import ALLOWANCE, VOLUME, assembly_check, export

    print('=== FreeCAD '+'.'.join(App.Version()[:3])+' · внешние поверхности, стойки и замки', flush=True)
    lifting_parts, wing_cuts = lifting.build()
    display_parts, gear_cuts = display.build()
    parts = hull.build(wing_cuts+gear_cuts) + lifting_parts + display_parts
    print('=== Проверка объёмных пересечений, посадочных плеч и устойчивости', flush=True)
    checks = assembly_check(parts)
    print(json.dumps(checks, ensure_ascii=False), flush=True)
    site = ROOT / 'site'
    with tempfile.TemporaryDirectory(prefix='buran-build-', dir=ROOT) as tmp:
        stage = Path(tmp)
        files = stage / 'files'
        stl = files / 'stl'
        stl.mkdir(parents=True)
        assets = stage / 'assets'
        assets.mkdir()
        metadata, calibration = [], []
        print('=== Экспорт и повторное чтение 12 STL и 2 калибров посадки', flush=True)
        for assembly, group, output in [(True, parts, metadata), (False, gauges(), calibration)]:
            for part in group:
                row = export(part, stl)
                row['sha256'] = hashlib.sha256((stl/(part['id']+'.stl')).read_bytes()).hexdigest()
                if assembly:
                    x,y,z = part['explode']
                    row.update(explode=[x*.001, z*.001, -y*.001], note=part['note'])
                output.append(row)
                print(f"{row['id']}: {row['facets']} facets; {row['printSize']} mm", flush=True)
        catalog = dict(scale='1:144', printer=VOLUME.tolist(), allowance=ALLOWANCE.tolist(),
                       unit='mm', supported=False, **checks, parts=metadata, gauges=calibration)
        with ZipFile(files/'Buran-STL.zip', 'w', compression=ZIP_DEFLATED, compresslevel=6) as archive:
            for part in metadata+calibration:
                path = stl/(part['id']+'.stl')
                archive.write(path, ('model/' if part in metadata else 'calibration/')+path.name)
            archive.writestr('print-layout.json', json.dumps(catalog, indent=2, ensure_ascii=False))
        print('=== Цветная браузерная модель из CAD-поверхностей', flush=True)
        scene = make_glb(parts)
        catalog['glb'] = base64.b64encode(scene).decode('ascii')
        (assets/'model-data.js').write_text('window.BURAN = '+json.dumps(catalog, ensure_ascii=False, separators=(',',':'))+';\n', encoding='utf-8')
        print('=== Нативные эскизы, лофт, вырезы и презентация сборки FreeCAD', flush=True)
        save_native(parts, files/'Buran-VDNH.FCStd')
        for name in ('files', 'assets'):
            for item in (stage/name).rglob('*'):
                if item.is_file():
                    destination = site/item.relative_to(stage)
                    destination.parent.mkdir(exist_ok=True, parents=True)
                    os.replace(item, destination)
    print('=== Готовы FCStd, цветная сцена, 14 STL и ZIP', flush=True)


if __name__ == '__main__':
    try:
        build()
    except BaseException:
        traceback.print_exc()
        result = 1
    else:
        result = 0
    # Qt and OCCT own process-wide singletons in the application Python distribution.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(result)
