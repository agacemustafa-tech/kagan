# OBJ (Kizilelma_1_Plane) -> game model JSON (int16 pos/normal, uint16 uv, uint16 indices)
import sys, json, base64, struct, io
import numpy as np
from PIL import Image
obj, col, out = sys.argv[1:4]
MATS = {  # [textured, r,g,b, spec, shininess, emissive]
 'Kizilelma_1':  ('body',    [1, 1, 1, 1, 1, 40, 0]),
 'grey_metal':   ('nozzle',  [0, 0.30, 0.30, 0.31, 0.9, 30, 0]),
 'black_glossy': ('sensor',  [0, 0.05, 0.06, 0.08, 1.6, 90, 0]),
 'black_matte':  ('engine',  [0, 0.09, 0.09, 0.10, 0.3, 20, 0]),
 'black_full':   ('intake',  [0, 0.04, 0.04, 0.045, 0.2, 10, 0]),
 'light':        ('light',   [0, 1.0, 0.92, 0.78, 0.5, 20, 1]),
}
V, T, N = [], [], []; faces = {}; on = False; mtl = None
for l in open(obj):
    t = l.split()
    if not t: continue
    if t[0] == 'o': on = l.strip() == 'o Kizilelma_1_Plane'
    elif t[0] == 'v': V.append([float(x) for x in t[1:4]])
    elif t[0] == 'vt': T.append([float(x) for x in t[1:3]])
    elif t[0] == 'vn': N.append([float(x) for x in t[1:4]])
    elif t[0] == 'usemtl': mtl = t[1]
    elif t[0] == 'f' and on:
        idx = [tuple(int(a) - 1 if a else -1 for a in (c.split('/') + ['', ''])[:3]) for c in t[1:]]
        faces.setdefault(mtl, []).extend([idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1))
V = np.array(V); N = np.array(N)
# drop the lowered landing gear: connected pieces that reach the ground
yb = V[[c[0] for fl in faces.values() for f in fl for c in f]][:, 1].min()
Lh = None
def comps(fl):
    par = {}
    def f_(a):
        while par.setdefault(a, a) != a: par[a] = par[par[a]]; a = par[a]
        return a
    for t in fl:
        for c in t[1:]: par[f_(c[0])] = f_(t[0][0])
    groups = {}
    for i, t in enumerate(fl): groups.setdefault(f_(t[0][0]), []).append(i)
    return groups.values()
x0_, x1_ = None, None
allx = V[[c[0] for fl in faces.values() for f in fl for c in f]][:, 0]; half0 = (allx.max() - allx.min()) / 2
dropped = 0
for m in list(faces):
    if m in ('light',): continue
    keep = []
    for g in comps(faces[m]):
        ys = V[[c[0] for i in g for c in faces[m][i]]][:, 1]
        low = (ys.min() - yb) / half0 < 0.09 and (m != 'Kizilelma_1' or ((ys.max() - yb) / half0 < 0.2 and len(g) < 120))
        if low: dropped += len(g)
        else: keep += [faces[m][i] for i in g]
    faces[m] = keep
print('dropped gear tris', dropped)
used = sorted({c[0] for fl in faces.values() for f in fl for c in f})
P = V[used]
x0, x1 = P[:, 0].min(), P[:, 0].max(); half = (x1 - x0) / 2; xm = (x0 + x1) / 2
zm = (P[:, 2].min() + P[:, 2].max()) / 2; ymin = P[:, 1].min()
def pos(p):  # nose (-x) -> -z, wingspan z -> x
    return [-(p[2] - zm) / half, (p[1] - ymin) / half, (p[0] - xm) / half]
def nrm(n):
    v = np.array([-n[2], n[1], n[0]]); return v / (np.linalg.norm(v) or 1)
q = lambda v: int(max(-32767, min(32767, round(v * 32767))))
geo = bytearray(); parts = []
for m, (name, mat) in MATS.items():
    if m not in faces: continue
    vmap = {}; vb = bytearray(); ib = []
    for f in faces[m]:
        for c in f:
            if c not in vmap:
                vmap[c] = len(vmap)
                p = pos(V[c[0]]); n = nrm(N[c[2]]) if c[2] >= 0 else [0, 1, 0]
                u, v = T[c[1]] if c[1] >= 0 else (0.5, 0.5)
                u = min(max(u, 0), 1); v = min(max(1 - v, 0), 1)
                vb += struct.pack('<hhhhhhHH', *[q(a) for a in p], *[q(a) for a in n], round(u * 65535), round(v * 65535))
            ib.append(vmap[c])
    assert len(vmap) < 65536
    vo = len(geo); geo += vb; io_ = len(geo); geo += struct.pack('<%dH' % len(ib), *ib)
    parts.append({'m': name, 'mat': mat, 'vo': vo, 'vc': len(vmap), 'io': io_, 'ic': len(ib)})
def uri(img, fmt, **kw):
    b = io.BytesIO(); img.save(b, fmt, **kw); return 'data:image/%s;base64,' % fmt.lower() + base64.b64encode(b.getvalue()).decode()
c = Image.open(col).convert('RGB').resize((1536, 1536), Image.LANCZOS)
tex = {'col': uri(c, 'JPEG', quality=82), 'nrm': uri(Image.new('RGB', (4, 4), (128, 128, 255)), 'PNG'),
       'spc': uri(Image.new('RGB', (4, 4), (150, 150, 150)), 'PNG')}
tex['col'] = tex['col'].replace('image/jpeg', 'image/jpeg')
d = {'geo': base64.b64encode(bytes(geo)).decode(), 'parts': parts, 'scale': 1, 'tex': tex}
open(out, 'w').write('const KZM=' + json.dumps(d, separators=(',', ':')) + ';')
P2 = np.array([pos(p) for p in P])
print('parts', [(p['m'], p['vc'], p['ic'] // 3) for p in parts])
print('bounds', P2.min(0).round(3), P2.max(0).round(3), 'bytes', len(open(out).read()))
