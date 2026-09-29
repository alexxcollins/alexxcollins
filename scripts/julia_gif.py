import numpy as np
from PIL import Image
W, H, N, ITERS = 540, 960, 72, 160
y, x = np.mgrid[-1.6:1.6:H*1j, -0.9:0.9:W*1j]
z0 = x + 1j * y

STOPS = np.array([[0.00, 8, 6, 30], [0.25, 40, 22, 90], [0.50, 150, 50, 130],
                  [0.72, 255, 120, 90], [0.88, 255, 200, 120], [1.00, 255, 248, 225]], float)
def palette(t):
    # sunset gradient: dark indigo far from the set, glowing cream at its edge
    t = np.clip(t, 0, 1)
    return np.stack([np.interp(t, STOPS[:, 0], STOPS[:, i]) for i in (1, 2, 3)], -1) / 255

# one shared 256-colour palette sampled from the gradient, so frames compress well
ref = Image.fromarray((np.concatenate([palette(np.linspace(0, 1, 255)), [[0.03, 0.02, 0.10]]])[None] * 255).astype(np.uint8))
pal = ref.quantize(colors=256)
frames = []
for k in range(N):
    th = 2*np.pi*k/N
    c = 0.7885 * np.exp(1j * th)  # classic Julia loop
    z = z0.copy(); n = np.zeros(z.shape); alive = np.ones(z.shape, bool)
    for i in range(ITERS):
        z[alive] = z[alive]**2 + c
        esc = alive & (np.abs(z) > 4)
        n[esc] = i + 1 - np.log2(np.log(np.abs(z[esc])))
        alive &= ~esc
    t = np.where(alive, 0, np.log1p(n) / np.log1p(ITERS * 0.35))
    rgb = palette(t)
    rgb[alive] = [0.03, 0.02, 0.10]
    frames.append(Image.fromarray((rgb*255).astype(np.uint8)).quantize(palette=pal, dither=Image.Dither.NONE))
frames[0].save("images/julia-wallpaper.gif", save_all=True, append_images=frames[1:], duration=80, loop=0, optimize=True)
