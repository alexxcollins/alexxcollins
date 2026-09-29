import math, random
W, H = 1080, 1920
random.seed(11)

def smooth_path(pts, bottom):
    # Catmull-Rom through pts -> cubic Béziers, closed down to the bottom edge
    d = [f"M0,{bottom} L{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    d.append(f"L{W},{bottom} Z")
    return " ".join(d)

def ridge(base, amp, n, seed):
    rnd = random.Random(seed)
    xs = [i * W / (n - 1) for i in range(n)]
    return [(x, base - amp * (0.45 + 0.55 * abs(math.sin(x / 210 + seed))) - rnd.uniform(0, amp * 0.35)) for x in xs]

stars = []
for _ in range(140):
    x, y = random.uniform(0, W), random.uniform(0, H * 0.4)
    r = random.choice([1.2, 1.5, 2, 2.6])
    o = 1 - y / (H * 0.45)
    stars.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff8e0" opacity="{o:.2f}"/>')

layers = [
    (ridge(1230, 230, 9, 1), "url(#m1)"),
    (ridge(1400, 190, 8, 3), "url(#m2)"),
    (ridge(1560, 140, 10, 5), "url(#m3)"),
]
mountains = "\n  ".join(f'<path d="{smooth_path(p, H)}" fill="{f}"/>' for p, f in layers)

def bird(x, y, s):
    return (f'<path d="M{x-s},{y} Q{x-s/2},{y-s*0.6} {x},{y} Q{x+s/2},{y-s*0.6} {x+s},{y}" '
            f'fill="none" stroke="#2a1838" stroke-width="{s/7:.1f}" stroke-linecap="round"/>')
birds = "\n  ".join(bird(*b) for b in [(300, 820, 26), (360, 790, 20), (410, 835, 16), (760, 760, 18)])

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
 <defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
   <stop offset="0" stop-color="#0f1450"/>
   <stop offset="0.35" stop-color="#4a2f6e"/>
   <stop offset="0.55" stop-color="#c0607a"/>
   <stop offset="0.68" stop-color="#ff9a6a"/>
   <stop offset="1" stop-color="#ffc98a"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
   <stop offset="0" stop-color="#ffe7a0" stop-opacity="0.75"/>
   <stop offset="1" stop-color="#ff9a6a" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="sun" cx="0.5" cy="0.45" r="0.55">
   <stop offset="0" stop-color="#fff4c2"/>
   <stop offset="0.6" stop-color="#ffd27a"/>
   <stop offset="1" stop-color="#ff9658"/>
  </radialGradient>
  <linearGradient id="m1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a4f86"/><stop offset="1" stop-color="#5c3474"/></linearGradient>
  <linearGradient id="m2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#55306e"/><stop offset="1" stop-color="#36204f"/></linearGradient>
  <linearGradient id="m3" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2c1a44"/><stop offset="1" stop-color="#150d24"/></linearGradient>
 </defs>
 <rect width="{W}" height="{H}" fill="url(#sky)"/>
 {"".join(stars)}
 <circle cx="540" cy="1150" r="520" fill="url(#glow)"/>
 <circle cx="540" cy="1150" r="250" fill="url(#sun)"/>
 {birds}
  {mountains}
 <text x="540" y="1735" text-anchor="middle" font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-weight="700" font-size="72" fill="#ffeedd">Hello from Claude</text>
 <text x="540" y="1805" text-anchor="middle" font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="38" fill="#ffeedd" opacity="0.8">drawn as vector art</text>
</svg>'''
open("images/sunset-vector.svg", "w").write(svg)
import cairosvg
cairosvg.svg2png(url="images/sunset-vector.svg", write_to="images/sunset-vector.png")
