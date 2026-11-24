# Recolour the Kizilelma livery: light blue-grey, no crescent-star / brand text, red-white roundels.
import sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
src, out = sys.argv[1], sys.argv[2]
im = np.asarray(Image.open(src).convert('RGB')).astype(float)
L = im.mean(-1)
BODY = 55.7
bg = np.abs(L-26) < 3          # unused UV space
light = L > 75                  # markings / text / roundels
light = ndimage.binary_dilation(light, iterations=3) & ~bg
# erase markings to the body tone
im[light] = [60, 55, 52]
L = im.mean(-1)
# light blue-grey like KAGAN; panel lines keep their relative darkness
target = np.array([200, 208, 218], float)
k = np.clip(L / BODY, 0, 1.15)[..., None]
out_im = np.clip(target * k, 0, 255)
out_im[bg] = target * 0.9
img = Image.fromarray(out_im.astype(np.uint8))
# roundels where the old ones were (ellipse = UV stretch of a circle on the airframe)
orig = np.asarray(Image.open(src).convert('RGB')).astype(float).mean(-1) > 100
regions = [(150,60,280,260),(1240,200,1440,460),(1680,1240,1900,1480),(990,1880,1160,2040),(510,1890,660,2040)]
mask = Image.fromarray((~bg).astype(np.uint8)*255)
layer = Image.new('RGB', img.size); lm = Image.new('L', img.size, 0)
d = ImageDraw.Draw(layer); dm = ImageDraw.Draw(lm)
RED, WHITE = (214, 32, 42), (245, 245, 245)
for x0,y0,x1,y1 in regions:
    sub = ndimage.binary_dilation(orig[y0:y1, x0:x1], iterations=5)
    lab, n = ndimage.label(sub); big = 1 + np.argmax(ndimage.sum(sub, lab, range(1, n + 1)))
    ys, xs = np.nonzero(lab == big); ys = ys; xs = xs
    bx0, bx1, by0, by1 = x0+xs.min(), x0+xs.max(), y0+ys.min(), y0+ys.max()
    cx, cy, rx, ry = (bx0+bx1)/2, (by0+by1)/2, (bx1-bx0)/2-4, (by1-by0)/2-4
    for f, c in [(1, RED), (.68, WHITE), (.36, RED)]:
        d.ellipse([cx-rx*f, cy-ry*f, cx+rx*f, cy+ry*f], fill=c)
    dm.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=255)
    print('roundel', round(cx), round(cy), round(rx), round(ry))
lm = Image.fromarray((np.asarray(lm) > 0) & (np.asarray(mask) > 0)).convert('L')
img.paste(layer, (0, 0), lm)
img.save(out, quality=90)
