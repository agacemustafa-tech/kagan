# Anka OBJ (3ds Max export, no .mtl) -> game model JSON. Landing gear and helper bones left out.
import sys, json, base64, struct, io
import numpy as np
from PIL import Image, ImageEnhance
obj, col, out = sys.argv[1:4]
# object -> (part name, material [textured, r,g,b, spec, shininess, emissive])
BODY = ('body', [1, 1, 1, 1, 1, 40, 0])
PARTS = {
 'Object088': BODY, 'Plane018': BODY, 'Object077': BODY, 'Object075': BODY,
 'Group39353': ('sensor', [0, 0.55, 0.58, 0.62, 0.8, 40, 0]), 'Object050': ('sensor', [0, 0.55, 0.58, 0.62, 0.8, 40, 0]),
 'Object049': ('sensor', [0, 0.55, 0.58, 0.62, 0.8, 40, 0]), 'Object035': ('glass', [0, 0.05, 0.06, 0.08, 2.0, 90, 0]),
 'Line072': ('pylon', [0, 0.42, 0.45, 0.49, 0.5, 30, 0]), 'Line022': ('pylon', [0, 0.42, 0.45, 0.49, 0.5, 30, 0]),
 'Object085': ('pylon', [0, 0.42, 0.45, 0.49, 0.5, 30, 0]), 'Object063': ('pylon', [0, 0.42, 0.45, 0.49, 0.5, 30, 0]),
 'Cylinder378': ('payload', [0, 0.78, 0.80, 0.80, 0.9, 40, 0]), 'Cylinder380': ('payload', [0, 0.78, 0.80, 0.80, 0.9, 40, 0]),
 'Cylinder381': ('payload', [0, 0.78, 0.80, 0.80, 0.9, 40, 0]), 'Cylinder382': ('payload', [0, 0.78, 0.80, 0.80, 0.9, 40, 0]),
 'Cylinder377': ('other', [0, 0.15, 0.15, 0.16, 0.6, 30, 0]), 'Cylinder376': ('other', [0, 0.30, 0.31, 0.33, 0.7, 30, 0]),
 'Mesh10': ('prop', [0, 0.12, 0.12, 0.13, 0.4, 20, 0]),
}
V, T, N = [], [], []; faces = {}; cur = None
for l in open(obj):
    if l.startswith('# object '): cur = l[9:].strip(); continue
    t = l.split()
    if not t: continue
    if t[0] == 'v': V.append([float(x) for x in t[1:4]])
    elif t[0] == 'vt': T.append([float(x) for x in t[1:3]])
    elif t[0] == 'vn': N.append([float(x) for x in t[1:4]])
    elif t[0] == 'f' and cur in PARTS:
        def ix(c):
            a = (c.split('/') + ['', ''])[:3]
            r = []
            for k, arr in zip(a, (V, T, N)):
                if not k: r.append(-1); continue
                k = int(k); r.append(k - 1 if k > 0 else len(arr) + k)
            return tuple(r)
        idx = [ix(c) for c in t[1:]]
        faces.setdefault(PARTS[cur][0], []).extend([idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1))
V = np.array(V); N = np.array(N)
mats = {v[0]: v[1] for v in PARTS.values()}
P = V[sorted({c[0] for fl in faces.values() for f in fl for c in f})]
xm = (P[:, 0].min() + P[:, 0].max()) / 2; ymin = P[:, 1].min()
zc = V[[c[0] for f in faces['body'] for c in f]][:, 2]
zm = (zc.min() + zc.max()) / 2; halfspan = (zc.max() - zc.min()) / 2
k = 0.75 / halfspan            # same convention as DOGAN (TB2): half span = 0.75
def pos(p): return [(p[2] - zm) * k, (p[1] - ymin) * k, -(p[0] - xm) * k]   # nose (+x) -> -z
def nrm(n):
    v = np.array([n[2], n[1], -n[0]]); return v / (np.linalg.norm(v) or 1)
q = lambda v: int(max(-32767, min(32767, round(v * 32767))))
# vertex-clustering decimation (keeps the file small enough for the phone)
CELL = float(sys.argv[4]) if len(sys.argv) > 4 else 0.006
def decimate(tris):
    key = {}; rep = {}; out_ = []; seen = set()
    for f in tris:
        cs = []
        for c in f:
            p = pos(V[c[0]]); kk = tuple(int(np.floor(a / CELL)) for a in p)
            if kk not in rep: rep[kk] = c
            cs.append(kk)
        if len(set(cs)) < 3: continue
        t = tuple(sorted(cs))
        if t in seen: continue
        seen.add(t); out_.append([rep[x] for x in cs])
    return out_
for n_ in list(faces):
    if n_ in ('prop',): continue
    b4 = len(faces[n_]); faces[n_] = decimate(faces[n_]); print(n_, b4, '->', len(faces[n_]))
geo = bytearray(); parts = []
for name in ['body', 'sensor', 'glass', 'pylon', 'payload', 'other', 'prop']:
    if name not in faces: continue
    tris = faces[name]
    for s in range(0, len(tris), 21000):       # uint16 index limit per part
        vmap = {}; vb = bytearray(); ib = []
        for f in tris[s:s + 21000]:
            for c in f:
                if c not in vmap:
                    vmap[c] = len(vmap)
                    p = pos(V[c[0]]); n = nrm(N[c[2]]) if c[2] >= 0 else [0, 1, 0]
                    u, v = T[c[1]] if c[1] >= 0 else (0.5, 0.5)
                    u = u - np.floor(u) if u > 1 or u < 0 else u; v = 1 - v; v = v - np.floor(v) if v > 1 or v < 0 else v
                    vb += struct.pack('<hhhhhhHH', *[q(a) for a in p], *[q(a) for a in n], round(u * 65535), round(v * 65535))
                ib.append(vmap[c])
        assert len(vmap) < 65536
        vo = len(geo); geo += vb; io_ = len(geo); geo += struct.pack('<%dH' % len(ib), *ib)
        if len(geo) % 4: geo += b'\0' * (4 - len(geo) % 4)
        parts.append({'m': name, 'mat': mats[name], 'vo': vo, 'vc': len(vmap), 'io': io_, 'ic': len(ib)})
def uri(img, fmt, **kw):
    b = io.BytesIO(); img.save(b, fmt, **kw); return 'data:image/%s;base64,' % fmt.lower() + base64.b64encode(b.getvalue()).decode()
c = Image.open(col).convert('RGB').resize((2048, 2048), Image.LANCZOS)
c = ImageEnhance.Brightness(c).enhance(1.18)
tex = {'col': uri(c, 'JPEG', quality=80), 'nrm': uri(Image.new('RGB', (4, 4), (128, 128, 255)), 'PNG'),
       'spc': uri(Image.new('RGB', (4, 4), (150, 150, 150)), 'PNG')}
d = {'geo': base64.b64encode(bytes(geo)).decode(), 'parts': parts, 'scale': 1, 'tex': tex}
open(out, 'w').write('const ANKAM=' + json.dumps(d, separators=(',', ':')) + ';')
P2 = np.array([pos(p) for p in P])
print('parts', [(p['m'], p['vc'], p['ic'] // 3) for p in parts])
print('bounds', P2.min(0).round(3), P2.max(0).round(3), 'bytes', len(open(out).read()))
