"""Build the tabletop USDZ from our own GLB with the Apple USD tools on macOS."""

from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZIP_STORED, ZipFile


def export(scene, parts, path):
    required = ('usdcat', 'usdzip', 'usdchecker')
    commands = {name: shutil.which(name) for name in required}
    if not all(commands.values()):
        raise RuntimeError('The complete release uses Apple USD Tools: usdcat, usdzip, usdchecker.')

    # The native viewer is Y-up, metres. Re-centre the stand on the table but
    # never fit the model to a generic 1 m box: its 1:144 scale is the point.
    bounds = [part['shape'].BoundBox for part in parts]
    mid_x = .5 * (min(b.XMin for b in bounds) + max(b.XMax for b in bounds))
    mid_y = .5 * (min(b.YMin for b in bounds) + max(b.YMax for b in bounds))
    low_z = min(b.ZMin for b in bounds)
    position = (-.001*mid_x, -.001*low_z, .001*mid_y)
    ground = '''#usda 1.0
(
    defaultPrim = "Buran"
    metersPerUnit = 1
    upAxis = "Y"
)
def Xform "Buran" {
    def Xform "Tabletop" (prepend references = @Exterior.usdc@) {
        double3 xformOp:translate = (%.8f, %.8f, %.8f)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
''' % position
    with tempfile.TemporaryDirectory(prefix='quick-look-', dir=path.parent.parent) as folder:
        cwd = Path(folder)
        (cwd/'Buran.glb').write_bytes(scene)
        (cwd/'Tabletop.usda').write_text(ground, encoding='utf-8')
        subprocess.run([commands['usdcat'], '--flatten', '--skipSourceFileComment',
                        'Buran.glb', '-o', 'Exterior.usdc'], cwd=cwd, check=True)
        subprocess.run([commands['usdcat'], '--flatten', '--skipSourceFileComment',
                        'Tabletop.usda', '-o', 'Tabletop.usdc'], cwd=cwd, check=True)
        subprocess.run([commands['usdzip'], '--arkitAsset', 'Tabletop.usdc', str(path.resolve())],
                       cwd=cwd, check=True)
        subprocess.run([commands['usdchecker'], '--arkit', str(path.resolve())], cwd=cwd, check=True)
    with ZipFile(path) as archive:
        root, = archive.infolist()
        if root.compress_type != ZIP_STORED or archive.read(root)[:8] != b'PXR-USDC':
            raise ValueError('Expected a self-contained USDZ with a single binary scene')
