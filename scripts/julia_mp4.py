"""Full-resolution MP4 version of julia_gif.py, playable on any phone."""
import subprocess
import numpy as np
import imageio_ffmpeg

W, H, N, ITERS, FPS, LOOPS = 1080, 1920, 144, 160, 24, 3
y, x = np.mgrid[-1.6:1.6:H*1j, -0.9:0.9:W*1j]
z0 = x + 1j * y

STOPS = np.array([[0.00, 8, 6, 30], [0.25, 40, 22, 90], [0.50, 150, 50, 130],
                  [0.72, 255, 120, 90], [0.88, 255, 200, 120], [1.00, 255, 248, 225]], float)
def palette(t):
    # sunset gradient: dark indigo far from the set, glowing cream at its edge
    t = np.clip(t, 0, 1)
    return np.stack([np.interp(t, STOPS[:, 0], STOPS[:, i]) for i in (1, 2, 3)], -1) / 255

def frame(k):
    c = 0.7885 * np.exp(2j * np.pi * k / N)  # classic Julia loop
    z = z0.copy(); n = np.zeros(z.shape); alive = np.ones(z.shape, bool)
    for i in range(ITERS):
        z[alive] = z[alive]**2 + c
        esc = alive & (np.abs(z) > 4)
        n[esc] = i + 1 - np.log2(np.log(np.abs(z[esc])))
        alive &= ~esc
    rgb = palette(np.where(alive, 0, np.log1p(n) / np.log1p(ITERS * 0.35)))
    rgb[alive] = [0.03, 0.02, 0.10]
    return (rgb * 255).astype(np.uint8)

one_loop = "images/.julia-loop.mp4"
w = imageio_ffmpeg.write_frames(one_loop, (W, H), fps=FPS, codec="libx264", quality=None, macro_block_size=8,
                                pix_fmt_out="yuv420p", output_params=["-crf", "24", "-preset", "slow"])
w.send(None)
for k in range(N):
    w.send(frame(k))
w.close()
# repeat the seamless loop so players that don't auto-loop still show it a few times
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-stream_loop", str(LOOPS - 1),
                "-i", one_loop, "-c", "copy", "-movflags", "+faststart", "images/julia-wallpaper.mp4"], check=True)
subprocess.run(["rm", one_loop])
