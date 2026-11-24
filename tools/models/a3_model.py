# Anka-3 OBJ (no texture shipped) -> game model JSON with a painted top-projection livery.
import sys, json, base64, struct, io
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
obj, out = sys.argv[1:3]
V, N, F = [], [], []
for l in open(obj):
    t = l.split()
    if not t: continue
    if t[0] == 'v': V.append([float(x) for x in t[1:4]])
    elif t[0] == 'vn': N.append([float(x) for x in t[1:4]])
    elif t[0] == 'f':
        idx = []
        for c in t[1:]:
            a = (c.split('/') + ['', ''])[:3]
            vi = int(a[0]); vi = vi - 1 if vi > 0 else len(V) + vi
            ni = int(a[2]) - 1 if a[2] else -1
            idx.append((vi, ni))
        F.extend([idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1))
V = np.array(V); N = np.array(N)
# connected components; drop landing gear (pieces reaching the ground, away from the wing)
par = list(range(len(V)))
def f_(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for t in F:
    for c in t[1:]: par[f_(c[0])] = f_(t[0][0])
groups = {}
for i, t in enumerate(F): groups.setdefault(f_(t[0][0]), []).append(i)
y0 = V[:, 1].min(); H = V[:, 1].max() - y0
keep = []
for g in groups.values():
    ys = V[[c[0] for i in g for c in F[i]]][:, 1]
    gear = (ys.min() - y0) < 0.08 * H and (ys.max() - y0) < 0.75 * H and len(g) < 4000
    print('comp', len(g), 'y', round(ys.min()), round(ys.max()), 'GEAR' if gear else '')
    if not gear: keep += [F[i] for i in g]
F = keep
P = V[sorted({c[0] for t in F for c in t})]
xm = (P[:, 0].min() + P[:, 0].max()) / 2; zm = (P[:, 2].min() + P[:, 2].max()) / 2; ymin = P[:, 1].min()
k = 0.75 / ((P[:, 0].max() - P[:, 0].min()) / 2)       # half span 0.75, like the other drones
def pos(p): return [-(p[0] - xm) * k, (p[1] - ymin) * k, -(p[2] - zm) * k]   # nose (+z) -> -z
def nrm(n):
    v = np.array([-n[0], n[1], -n[2]]); return v / (np.linalg.norm(v) or 1)
PP = np.array([pos(p) for p in P]); ZH = np.abs(PP[:, 2]).max()
def uv(p): return ((p[0] / 0.75 + 1) / 2, (p[2] / ZH + 1) / 2)
# --- livery: top-view projection, light grey, edge shading, red-white roundels on the wings ---
S = 1024
mask = Image.new('L', (S, S), 0); md = ImageDraw.Draw(mask)
for t in F:
    md.polygon([(uv(pos(V[c[0]]))[0] * S, uv(pos(V[c[0]]))[1] * S) for c in t], fill=255)
m = np.asarray(mask) > 0
base = np.zeros((S, S, 3), float) + [196, 204, 214]
yy = np.linspace(0, 1, S)[:, None]
base *= (0.96 + 0.06 * yy)[..., None]
edge = np.asarray(mask.filter(ImageFilter.GaussianBlur(10))) / 255.0
base *= (0.86 + 0.14 * np.clip(edge * 1.6, 0, 1))[..., None]
img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)
# faint panel lines across the wing
for i in range(1, 7):
    zz = int(S * (0.2 + i * 0.09)); d.line([(0, zz), (S, zz)], fill=(176, 184, 194), width=2)
d.line([(S // 2, 0), (S // 2, S)], fill=(176, 184, 194), width=2)
# roundels on each wing where the wing is wide enough
rows = np.nonzero(m[:, int(S * 0.78)])[0]
cy = int(rows.mean()) if len(rows) else int(S * 0.75)
for cx in (int(S * 0.22), int(S * 0.78)):
    for f, c in [(30, (214, 32, 42)), (20, (245, 245, 245)), (10, (214, 32, 42))]:
        d.ellipse([cx - f, cy - f * 1.25, cx + f, cy + f * 1.25], fill=c)  # v is squashed (length < span)
d.text((S // 2 + 40, int(S * 0.35)), 'KR-01', fill=(90, 98, 108))
print('roundel row', cy)
q = lambda v: int(max(-32767, min(32767, round(v * 32767))))
vmap = {}; vb = bytearray(); ib = []
for t in F:
    for c in t:
        if c not in vmap:
            vmap[c] = len(vmap); p = pos(V[c[0]]); n = nrm(N[c[1]]) if c[1] >= 0 else [0, 1, 0]; u, v = uv(p)
            vb += struct.pack('<hhhhhhHH', *[q(a) for a in p], *[q(a) for a in n], round(min(max(u, 0), 1) * 65535), round(min(max(v, 0), 1) * 65535))
        ib.append(vmap[c])
assert len(vmap) < 65536
geo = bytearray(vb); io_ = len(geo); geo += struct.pack('<%dH' % len(ib), *ib)
parts = [{'m': 'body', 'mat': [1, 1, 1, 1, 1.1, 45, 0], 'vo': 0, 'vc': len(vmap), 'io': io_, 'ic': len(ib)}]
def uri(im, fmt, **kw):
    b = io.BytesIO(); im.save(b, fmt, **kw); return 'data:image/%s;base64,' % fmt.lower() + base64.b64encode(b.getvalue()).decode()
img.save('/tmp/a3tex.png')
tex = {'col': uri(img, 'JPEG', quality=85), 'nrm': uri(Image.new('RGB', (4, 4), (128, 128, 255)), 'PNG'),
       'spc': uri(Image.new('RGB', (4, 4), (150, 150, 150)), 'PNG')}
open(out, 'w').write('const ANKA3M=' + json.dumps({'geo': base64.b64encode(bytes(geo)).decode(), 'parts': parts, 'scale': 1, 'tex': tex}, separators=(',', ':')) + ';')
print('verts', len(vmap), 'tris', len(ib) // 3, 'bounds', PP.min(0).round(3), PP.max(0).round(3), 'bytes', len(open(out).read()))
