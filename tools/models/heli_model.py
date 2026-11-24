# T129-type attack helicopter OBJ -> game model JSON. Light grey instead of the dark green; wheels left out.
# Main and tail rotor go in a part named 'rotor' that the in-game sprite skips (the game draws spinning blades itself).
import sys, json, base64, struct, io
import numpy as np
from PIL import Image
obj, out = sys.argv[1:3]
MAT = {'02___Default': ('body', [0, 0.74, 0.77, 0.80, 0.9, 40, 0]), '03___Default': ('body2', [0, 0.56, 0.60, 0.64, 0.7, 30, 0]),
       'wire_141173118': ('body2', [0, 0.56, 0.60, 0.64, 0.7, 30, 0]), '01___Default': ('glass', [0, 0.06, 0.09, 0.13, 2.2, 110, 0]),
       '08___Default': ('metal', [0, 0.30, 0.31, 0.33, 0.8, 30, 0]), '07___Default': ('metal', [0, 0.30, 0.31, 0.33, 0.8, 30, 0]),
       'wire_008008008': ('rotor', [0, 0.10, 0.10, 0.11, 0.4, 20, 0]), 'wire_004004004': ('rotor', [0, 0.10, 0.10, 0.11, 0.4, 20, 0]),
       'wire_000000000': ('metal', [0, 0.08, 0.08, 0.09, 0.3, 20, 0])}
SKIP = {'Cylinder001', 'Cylinder002', 'Cylinder006'}   # wheels
V, N = [], []; faces = {}; g = None; mtl = None
for l in open(obj):
    t = l.split()
    if not t: continue
    if t[0] == 'g': g = t[1] if len(t) > 1 else None
    elif t[0] == 'v': V.append([float(x) for x in t[1:4]])
    elif t[0] == 'vn': N.append([float(x) for x in t[1:4]])
    elif t[0] == 'usemtl': mtl = t[1]
    elif t[0] == 'f' and g not in SKIP:
        name = 'rotor' if g in ('er', 'Cylinder003') else MAT[mtl][0]
        idx = []
        for c in t[1:]:
            a = (c.split('/') + ['', ''])[:3]
            vi = int(a[0]); vi = vi - 1 if vi > 0 else len(V) + vi
            ni = int(a[2]) if a[2] else 0; ni = ni - 1 if ni > 0 else (len(N) + ni if ni < 0 else -1)
            idx.append((vi, ni))
        faces.setdefault(name, []).extend([idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1))
mats = {v[0]: v[1] for v in MAT.values()}; mats['rotor'] = MAT['wire_008008008'][1]
V = np.array(V); N = np.array(N)
P = V[sorted({c[0] for fl in faces.values() for f in fl for c in f})]
B = V[sorted({c[0] for n in faces if n != 'rotor' for f in faces[n] for c in f})]
xm = (B[:, 0].min() + B[:, 0].max()) / 2; ym = (B[:, 1].min() + B[:, 1].max()) / 2; zmin = B[:, 2].min()
k = 0.8 / ((B[:, 1].max() - B[:, 1].min()) / 2)      # fuselage half length 0.8 (a little smaller than the jets)
def pos(p): return [-(p[0] - xm) * k, (p[2] - zmin) * k, (p[1] - ym) * k]   # nose (-y) -> -z, z up -> y up
def nrm(n):
    v = np.array([-n[0], n[2], n[1]]); return v / (np.linalg.norm(v) or 1)
q = lambda v: int(max(-32767, min(32767, round(v * 32767))))
geo = bytearray(); parts = []
for name in ['body', 'body2', 'glass', 'metal', 'rotor']:
    if name not in faces: continue
    vmap = {}; vb = bytearray(); ib = []
    for f in faces[name]:
        for c in f:
            if c not in vmap:
                vmap[c] = len(vmap); p = pos(V[c[0]]); n = nrm(N[c[1]]) if c[1] >= 0 else [0, 1, 0]
                vb += struct.pack('<hhhhhhHH', *[q(a) for a in p], *[q(a) for a in n], 0, 0)
            ib.append(vmap[c])
    assert len(vmap) < 65536
    vo = len(geo); geo += vb; io_ = len(geo); geo += struct.pack('<%dH' % len(ib), *ib)
    if len(geo) % 4: geo += b'\0' * (4 - len(geo) % 4)
    parts.append({'m': name, 'mat': mats[name], 'vo': vo, 'vc': len(vmap), 'io': io_, 'ic': len(ib)})
def uri(im):
    b = io.BytesIO(); im.save(b, 'PNG'); return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()
tex = {'col': uri(Image.new('RGB', (4, 4), (200, 205, 212))), 'nrm': uri(Image.new('RGB', (4, 4), (128, 128, 255))), 'spc': uri(Image.new('RGB', (4, 4), (150, 150, 150)))}
open(out, 'w').write('const HELIM=' + json.dumps({'geo': base64.b64encode(bytes(geo)).decode(), 'parts': parts, 'scale': 1, 'tex': tex}, separators=(',', ':')) + ';')
PP = np.array([pos(p) for p in P])
print('parts', [(p['m'], p['vc'], p['ic'] // 3) for p in parts], 'bounds', PP.min(0).round(3), PP.max(0).round(3), 'bytes', len(open(out).read()))
