"""Cartoon: Dad vs the scotch bonnet.

scene(t) returns an SVG for time t in [0, 1]; the whole story is driven by t:
  0.00-0.20  calm, spoon with chilli goes in
  0.20-0.42  the heat builds (face turns red from the chin up)
  0.42-0.80  meltdown: fire breath, steam, sweat, water glugged
  0.80-1.00  aftermath and the final score
Run it to write a still PNG, a GIF and an MP4 into images/.
"""
import io
import math
import random
import subprocess

import cairosvg
import imageio_ffmpeg
import numpy as np
from PIL import Image

W, H = 1080, 1920
SKIN, RED = (242, 196, 164), (232, 62, 52)
FONT = "Bangers, DejaVu Sans, sans-serif"


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    """0 before a, 1 after b, smooth in between."""
    x = clamp((t - a) / (b - a))
    return x * x * (3 - 2 * x)


def lerp(a, b, x):
    return a + (b - a) * x


def mix(c1, c2, x):
    return "#%02x%02x%02x" % tuple(int(lerp(c1[i], c2[i], x)) for i in range(3))


def text(x, y, s, size, fill="#fff", stroke="#231a2e", sw=10, anchor="middle", extra=""):
    # outlined comic lettering: stroke underneath, fill on top
    base = f'x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" text-anchor="{anchor}" {extra}'
    return (f'<text {base} fill="{stroke}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round">{s}</text>'
            f'<text {base} fill="{fill}">{s}</text>')


def chilli(x, y, s=1.0, rot=0, face=False):
    """Scotch bonnet: squat, lobed, lantern-shaped, with a green cap."""
    g = [f'<g transform="translate({x},{y}) rotate({rot}) scale({s})">',
         '<path d="M-48,-10 C-60,-45 -25,-58 0,-50 C25,-58 60,-45 48,-10 '
         'C62,20 40,55 18,48 C8,62 -8,62 -18,48 C-40,55 -62,20 -48,-10 Z" '
         'fill="#f0451f" stroke="#7a1c0c" stroke-width="5"/>',
         '<path d="M-22,-35 C-30,-10 -26,20 -16,38" stroke="#ff8a5c" stroke-width="7" fill="none" stroke-linecap="round" opacity="0.7"/>',
         '<path d="M-22,-50 Q0,-68 22,-50 Q0,-42 -22,-50 Z" fill="#3f8a2e" stroke="#1f4a17" stroke-width="4"/>',
         '<path d="M0,-58 Q4,-80 16,-86" stroke="#3f8a2e" stroke-width="8" fill="none" stroke-linecap="round"/>']
    if face:  # the villain: narrowed eyes and a smirk
        g += ['<path d="M-26,-14 L-8,-8 M26,-14 L8,-8" stroke="#2a0f08" stroke-width="6" stroke-linecap="round"/>',
              '<circle cx="-15" cy="0" r="6" fill="#2a0f08"/><circle cx="15" cy="0" r="6" fill="#2a0f08"/>',
              '<path d="M-18,20 Q2,36 22,14" stroke="#2a0f08" stroke-width="6" fill="none" stroke-linecap="round"/>']
    g.append('</g>')
    return "".join(g)


def flames(cx, cy, t, power):
    """Fire breath blasting out to the left from (cx, cy)."""
    if power <= 0:
        return ""
    rnd = random.Random(int(t * 1000))
    out = []
    for col, scale in [("#e8331c", 1.0), ("#ff8a1f", 0.72), ("#ffd84a", 0.45)]:
        L = 430 * power * scale * rnd.uniform(0.9, 1.1)
        h = 120 * power * scale
        pts = [f"M{cx},{cy - 18 * scale}"]
        n = 6
        for i in range(1, n + 1):
            x = cx - L * i / n
            spread = h * (i / n) ** 0.7
            pts.append(f"Q{x + L / n / 2},{cy - spread - rnd.uniform(0, 40) * scale} {x},{cy - spread * 0.6}")
        pts.append(f"Q{cx - L * 1.08},{cy} {cx - L},{cy + h * 0.6}")
        for i in range(n, 0, -1):
            x = cx - L * i / n
            spread = h * (i / n) ** 0.7
            pts.append(f"Q{x + L / n / 2},{cy + spread + rnd.uniform(0, 40) * scale} {x + L / n},{cy + spread * 0.6}")
        pts.append(f"L{cx},{cy + 18 * scale} Z")
        out.append(f'<path d="{" ".join(pts)}" fill="{col}" opacity="0.95"/>')
    return "".join(out)


def sweat(t, amount):
    if amount <= 0:
        return ""
    out = []
    for i in range(10):
        ang = math.radians(-160 + i * 16 + (7 if i % 2 else 0))
        ph = (t * 6 + i * 0.37) % 1
        r = 230 + 170 * ph
        x, y = 540 + r * math.cos(ang), 760 + r * math.sin(ang) * 0.9 + 60 * ph * ph
        a = math.degrees(ang) + 90
        out.append(f'<path transform="translate({x:.1f},{y:.1f}) rotate({a:.0f}) scale({0.9 + 0.4 * (i % 3) / 2})" '
                   f'd="M0,-22 C10,-6 14,4 14,10 A14,14 0 0 1 -14,10 C-14,4 -10,-6 0,-22 Z" '
                   f'fill="#8fd3ff" stroke="#2b6fa0" stroke-width="3" opacity="{amount * (1 - ph * 0.6):.2f}"/>')
    return "".join(out)


def steam(t, amount):
    if amount <= 0:
        return ""
    out = []
    for ex, dirn in [(355, -1), (725, 1)]:
        for i in range(4):
            ph = (t * 5 + i / 4) % 1
            x = ex + dirn * (20 + 60 * ph) + 15 * math.sin(ph * 9 + i)
            y = 770 - 260 * ph
            r = 22 + 40 * ph
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#ffffff" '
                       f'stroke="#c9c4d6" stroke-width="3" opacity="{amount * (1 - ph):.2f}"/>')
    return "".join(out)


def background():
    s = ['<rect width="1080" height="1920" fill="#e7e3e8"/>',
         # mountain panorama on the wall
         '<rect x="110" y="150" width="880" height="410" fill="url(#sky)" stroke="#2b2b35" stroke-width="10"/>',
         '<path d="M120,470 L260,330 L330,380 L470,230 L560,300 L640,250 L760,360 L850,300 L980,420 L980,550 L120,550 Z" fill="#5d6b86"/>',
         '<path d="M420,290 L470,230 L520,268 L495,262 L470,285 L445,270 Z M600,280 L640,250 L690,295 L660,285 L640,300 Z '
         'M230,360 L260,330 L300,362 L275,355 Z M820,320 L850,300 L890,335 L860,328 Z" fill="#ffffff"/>',
         '<path d="M120,550 L120,500 L300,450 L480,480 L700,430 L980,480 L980,550 Z" fill="#3c4760"/>']
    # prayer-flag bunting across the painting
    cols = ["#e9443a", "#f2c230", "#3f9b4a", "#2f6fd0", "#f7f7f7"]
    s.append('<path d="M540,520 Q760,560 1000,420" stroke="#6b5a4a" stroke-width="3" fill="none"/>')
    for i in range(12):
        u = i / 11
        x = (1 - u) ** 2 * 540 + 2 * (1 - u) * u * 760 + u * u * 1000
        y = (1 - u) ** 2 * 520 + 2 * (1 - u) * u * 560 + u * u * 420
        s.append(f'<rect x="{x - 12:.0f}" y="{y:.0f}" width="24" height="30" fill="{cols[i % 5]}" stroke="#5a4a3a" stroke-width="2"/>')
    # shelves behind
    s.append('<rect x="700" y="760" width="380" height="500" fill="#8a5a3a"/>'
             '<rect x="715" y="780" width="350" height="140" fill="#5e3c26"/><rect x="715" y="940" width="350" height="140" fill="#5e3c26"/>')
    for i, c in enumerate(["#f2c230", "#e9443a", "#3f9b4a", "#2f6fd0", "#f27ab0", "#ffffff", "#f2c230"]):
        s.append(f'<rect x="{725 + i * 48}" y="{820 - (i % 3) * 12}" width="40" height="{100 + (i % 3) * 12}" fill="{c}" opacity="0.85"/>')
    return "".join(s)


def daughter(t, laugh):
    bob = 6 * math.sin(t * 40) * laugh
    g = [f'<g transform="translate(880,{1030 + bob:.1f}) scale(0.62)">',
         '<path d="M-150,260 C-140,120 -80,90 0,88 C80,90 140,120 150,260 Z" fill="#fbfbf7" stroke="#2b2b35" stroke-width="5"/>',
         '<path d="M-150,170 L-120,165 M150,170 L120,165" stroke="#2f6a5a" stroke-width="10"/>',
         '<path d="M-40,90 L0,140 L40,90" fill="none" stroke="#2f6a5a" stroke-width="7"/>',
         '<ellipse cx="0" cy="-20" rx="95" ry="110" fill="#f5d2b8" stroke="#2b2b35" stroke-width="5"/>',
         '<path d="M-108,10 C-130,-110 -60,-150 0,-145 C70,-150 130,-110 108,10 C100,-50 70,-95 0,-98 C-70,-95 -100,-50 -108,10 Z" '
         'fill="#f0d27a" stroke="#b8942e" stroke-width="5"/>',
         '<path d="M-105,0 C-125,60 -110,110 -90,130 M105,0 C125,60 110,110 90,130" stroke="#f0d27a" stroke-width="24" fill="none" stroke-linecap="round"/>']
    if laugh > 0.5:  # eyes squeezed shut laughing, big open grin
        g += ['<path d="M-50,-25 Q-35,-40 -20,-25 M20,-25 Q35,-40 50,-25" stroke="#2b2b35" stroke-width="7" fill="none" stroke-linecap="round"/>',
              '<path d="M-45,25 Q0,95 45,25 Z" fill="#8a2a2a" stroke="#2b2b35" stroke-width="5"/>',
              '<path d="M-38,28 L38,28 L32,40 L-32,40 Z" fill="#fff"/>']
    else:
        g += ['<circle cx="-35" cy="-25" r="9" fill="#2b2b35"/><circle cx="35" cy="-25" r="9" fill="#2b2b35"/>',
              '<path d="M-35,30 Q0,60 35,30" stroke="#2b2b35" stroke-width="6" fill="none" stroke-linecap="round"/>']
    g += ['<circle cx="-62" cy="15" r="16" fill="#f59a8a" opacity="0.6"/><circle cx="62" cy="15" r="16" fill="#f59a8a" opacity="0.6"/>', '</g>']
    if laugh > 0.5:
        g.append(text(960 + 8 * math.sin(t * 50), 915, "HA HA!", 64, fill="#f2c230", sw=9, extra='transform="rotate(8 960 915)"'))
    return "".join(g)


def dad_head(t, heat, phase, jitter):
    rnd = random.Random(int(t * 997))
    jx, jy = rnd.uniform(-1, 1) * 9 * jitter, rnd.uniform(-1, 1) * 6 * jitter
    edge = 1 - heat  # red rises from the chin up
    g = [f'<g transform="translate({jx:.1f},{jy:.1f})">',
         f'<defs><linearGradient id="face" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{mix(SKIN, RED, heat * 0.35)}"/>'
         f'<stop offset="{clamp(edge - 0.08):.3f}" stop-color="{mix(SKIN, RED, heat * 0.35)}"/>'
         f'<stop offset="{clamp(edge + 0.08):.3f}" stop-color="{mix(SKIN, RED, heat)}"/>'
         f'<stop offset="1" stop-color="{mix(SKIN, RED, heat)}"/></linearGradient></defs>',
         # neck
         '<rect x="485" y="940" width="110" height="130" fill="url(#face)" stroke="#3a2a22" stroke-width="5"/>',
         # ears
         '<ellipse cx="368" cy="800" rx="32" ry="52" fill="url(#face)" stroke="#3a2a22" stroke-width="5"/>',
         '<ellipse cx="712" cy="800" rx="32" ry="52" fill="url(#face)" stroke="#3a2a22" stroke-width="5"/>',
         # head
         '<ellipse cx="540" cy="780" rx="178" ry="218" fill="url(#face)" stroke="#3a2a22" stroke-width="6"/>',
         # short, slightly receding brown hair
         '<path d="M372,720 C360,585 440,548 540,550 C645,546 722,590 708,720 C700,660 670,628 628,618 '
         'C600,600 560,612 540,606 C515,612 470,600 450,615 C410,628 382,665 372,720 Z" fill="#6f523c" stroke="#3a2a22" stroke-width="5"/>']
    # eyebrows
    lift = 22 * seg(t, 0.2, 0.3) if phase in ("heat", "melt") else 0
    if phase == "melt":
        g.append('<path d="M420,672 L505,700 M660,672 L575,700" stroke="#4a3526" stroke-width="12" stroke-linecap="round"/>')
    else:
        g.append(f'<path d="M425,{690 - lift} Q470,{668 - lift} 510,{688 - lift} M570,{688 - lift} Q610,{668 - lift} 655,{690 - lift}" '
                 'stroke="#4a3526" stroke-width="11" fill="none" stroke-linecap="round"/>')
    # eyes
    if phase == "calm":
        g.append('<path d="M450,778 Q472,760 494,778 M590,778 Q612,760 634,778" stroke="#2b2b35" stroke-width="8" fill="none" stroke-linecap="round"/>')
    elif phase == "heat":
        g.append('<circle cx="472" cy="772" r="30" fill="#fff" stroke="#2b2b35" stroke-width="4"/>'
                 '<circle cx="612" cy="772" r="30" fill="#fff" stroke="#2b2b35" stroke-width="4"/>'
                 '<circle cx="472" cy="772" r="9" fill="#2b2b35"/><circle cx="612" cy="772" r="9" fill="#2b2b35"/>')
    else:  # squeezed shut with streaming tears
        g.append('<path d="M448,758 L495,775 L448,792 M636,758 L589,775 L636,792" stroke="#2b2b35" stroke-width="9" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        for x, d in [(455, -1), (628, 1)]:
            ph = (t * 8) % 1
            g.append(f'<path d="M{x},795 Q{x + d * 20},{850} {x + d * 10},{900 + 40 * ph}" stroke="#8fd3ff" stroke-width="14" fill="none" stroke-linecap="round" opacity="0.9"/>')
    # round tortoiseshell glasses
    g.append('<g fill="#cfe8ff" fill-opacity="0.18" stroke="#5a3f2c" stroke-width="13">'
             '<circle cx="472" cy="772" r="68"/><circle cx="612" cy="772" r="68"/></g>'
             '<path d="M530,762 Q542,748 554,762" stroke="#5a3f2c" stroke-width="11" fill="none"/>'
             '<path d="M404,764 L368,778 M680,764 L712,778" stroke="#5a3f2c" stroke-width="11" stroke-linecap="round"/>'
             '<path d="M440,735 L460,722 M580,735 L600,722" stroke="#ffffff" stroke-width="7" stroke-linecap="round" opacity="0.8"/>')
    # nose
    g.append('<path d="M545,790 Q522,845 548,858 Q562,860 568,850" stroke="#3a2a22" stroke-width="6" fill="none" stroke-linecap="round"/>')
    # mouth
    if phase == "calm":
        g.append('<path d="M468,888 Q540,968 612,888 Q540,912 468,888 Z" fill="#fff" stroke="#3a2a22" stroke-width="6" stroke-linejoin="round"/>')
    elif phase == "chew":
        g.append('<path d="M480,905 Q500,895 520,908 Q540,920 560,906 Q580,894 600,905" stroke="#3a2a22" stroke-width="7" fill="none" stroke-linecap="round"/>'
                 '<circle cx="455" cy="880" r="30" fill="#f59a8a" opacity="0.5"/><circle cx="625" cy="880" r="30" fill="#f59a8a" opacity="0.5"/>')
    elif phase == "heat":
        g.append('<path d="M495,915 Q540,890 585,915" stroke="#3a2a22" stroke-width="8" fill="none" stroke-linecap="round"/>'
                 '<path d="M600,905 Q615,915 610,930" stroke="#3a2a22" stroke-width="5" fill="none"/>')
    else:
        g.append('<ellipse cx="540" cy="915" rx="62" ry="52" fill="#6a1410" stroke="#3a2a22" stroke-width="6"/>'
                 '<ellipse cx="540" cy="945" rx="38" ry="20" fill="#e2585a"/>'
                 '<path d="M485,885 Q540,875 595,885 L590,898 Q540,890 490,898 Z" fill="#fff"/>')
    g.append('</g>')
    return "".join(g), (540 + jx, 915 + jy)


def glass(x, y, rot, level):
    top, bot = -150, 150
    wl = bot - (bot - top) * level
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f})">'
            f'<clipPath id="gl"><path d="M-55,{top} L55,{top} L45,{bot} L-45,{bot} Z"/></clipPath>'
            f'<rect x="-60" y="{wl:.1f}" width="120" height="{bot - wl + 5:.1f}" fill="#8fd3ff" opacity="0.85" clip-path="url(#gl)"/>'
            f'<path d="M-55,{top} L55,{top} L45,{bot} L-45,{bot} Z" fill="#ffffff" fill-opacity="0.25" stroke="#4d6d86" stroke-width="6"/>'
            f'<path d="M-35,{top + 20} L-28,{bot - 20}" stroke="#ffffff" stroke-width="8" opacity="0.8"/></g>')


def bottle(x, y, sc=0.75):
    return (f'<g transform="translate({x},{y}) scale({sc})">'
            '<path d="M-30,-120 L-30,-150 L-18,-165 L-18,-185 L18,-185 L18,-165 L30,-150 L30,-120 L30,0 L-30,0 Z" '
            'fill="#dff1ff" fill-opacity="0.6" stroke="#4d6d86" stroke-width="5"/>'
            '<rect x="-20" y="-195" width="40" height="14" fill="#2f6fd0"/>'
            '<rect x="-30" y="-95" width="60" height="40" fill="#2f6fd0" opacity="0.8"/>'
            f'{text(0, -64, "1L", 30, fill="#fff", sw=0)}</g>')


def arm(sh, el, hand, skin):
    pts = f"M{sh[0]:.0f},{sh[1]:.0f} L{el[0]:.0f},{el[1]:.0f} L{hand[0]:.0f},{hand[1]:.0f}"
    sx, sy = lerp(sh[0], el[0], 0.45), lerp(sh[1], el[1], 0.45)
    sleeve = f"M{sh[0]:.0f},{sh[1]:.0f} L{sx:.0f},{sy:.0f}"
    return (f'<path d="{pts}" stroke="#3a2a22" stroke-width="68" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{pts}" stroke="{skin}" stroke-width="56" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{sleeve}" stroke="#2b2b35" stroke-width="96" fill="none" stroke-linecap="round"/>'
            f'<path d="{sleeve}" stroke="#fbfaf3" stroke-width="84" fill="none" stroke-linecap="round"/>'
            f'<circle cx="{hand[0]:.0f}" cy="{hand[1]:.0f}" r="38" fill="{skin}" stroke="#3a2a22" stroke-width="6"/>')


def scene(t):
    heat = seg(t, 0.22, 0.45) * (1 - 0.35 * seg(t, 0.85, 1.0))
    phase = "calm" if t < 0.17 else "chew" if t < 0.24 else "heat" if t < 0.42 else "melt"
    drinking = seg(t, 0.60, 0.66) * (1 - seg(t, 0.80, 0.86))
    fire = seg(t, 0.42, 0.46) * (1 - seg(t, 0.58, 0.62)) + seg(t, 0.86, 0.9) * 0.0
    litres = 3 * seg(t, 0.62, 0.84)

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920" width="1080" height="1920">',
             '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c4fa0"/>'
             '<stop offset="1" stop-color="#7fb2e8"/></linearGradient>'
             '<linearGradient id="wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c8905c"/>'
             '<stop offset="1" stop-color="#94613a"/></linearGradient></defs>',
             background(),
             daughter(t, seg(t, 0.44, 0.5))]

    # body: white T-shirt with the red stripes
    parts.append('<path d="M240,1330 C250,1135 370,1070 480,1050 L600,1050 C710,1070 830,1135 840,1330 Z" fill="#fbfaf3" stroke="#2b2b35" stroke-width="6"/>'
                 '<path d="M480,1050 Q540,1110 600,1050" fill="none" stroke="#2b2b35" stroke-width="6"/>'
                 '<path d="M330,1170 L310,1300 M370,1165 L350,1300" stroke="#e05a4f" stroke-width="18"/>'
                 '<path d="M320,1230 L395,1215 L385,1280 Z" fill="#3b5fc0" opacity="0.8"/>')

    head, mouth = dad_head(t, heat, phase, jitter=seg(t, 0.42, 0.46) * (1 - drinking) * (1 - seg(t, 0.84, 0.9)))
    parts.append(steam(t, seg(t, 0.40, 0.46) * (1 - 0.7 * seg(t, 0.86, 1))))
    parts.append(head)
    parts.append(sweat(t, seg(t, 0.30, 0.42)))
    parts.append(flames(mouth[0] - 40, mouth[1], t, fire))

    # table
    parts.append('<rect x="0" y="1260" width="1080" height="660" fill="url(#wood)"/>'
                 '<path d="M0,1260 L1080,1260" stroke="#6e4526" stroke-width="8"/>')
    for i in range(7):
        y = 1320 + i * 90
        parts.append(f'<path d="M0,{y} C300,{y - 20} 700,{y + 25} 1080,{y - 10}" stroke="#86552f" stroke-width="4" fill="none" opacity="0.6"/>')

    # the bowl of stir-fry
    parts.append('<ellipse cx="420" cy="1600" rx="290" ry="95" fill="#ffffff" stroke="#2b2b35" stroke-width="6"/>'
                 '<path d="M130,1600 Q140,1720 420,1730 Q700,1720 710,1600" fill="#f4f4f4" stroke="#2b2b35" stroke-width="6"/>'
                 '<ellipse cx="420" cy="1600" rx="290" ry="95" fill="none" stroke="#2f6fd0" stroke-width="6"/>'
                 '<ellipse cx="420" cy="1590" rx="240" ry="65" fill="#d8b04a"/>')
    rnd = random.Random(3)
    for _ in range(38):
        x, y = rnd.uniform(210, 630), rnd.uniform(1545, 1630)
        if ((x - 420) / 240) ** 2 + ((y - 1590) / 65) ** 2 > 0.85:
            continue
        c = rnd.choice(["#f07a28", "#3f9b4a", "#2e7a33", "#6b2f5a", "#f2d27a", "#7cc05a"])
        parts.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rnd.uniform(10, 24):.0f}" ry="{rnd.uniform(6, 12):.0f}" '
                     f'transform="rotate({rnd.uniform(-40, 40):.0f} {x:.0f} {y:.0f})" fill="{c}"/>')

    # the villain chilli on the table, smirking
    parts.append(chilli(820, 1720, 1.15, rot=-8, face=True))
    if t > 0.44:
        parts.append(text(830, 1600, "HEH HEH", 46, fill="#f0451f", sw=8, extra='transform="rotate(-6 830 1600)"'))

    # left arm lifts a spoon with a chilli on it, then rests
    lift = seg(t, 0.02, 0.15) * (1 - seg(t, 0.17, 0.25))
    hx, hy = lerp(440, 470, lift), lerp(1370, 980, lift)
    arm_skin = mix(SKIN, RED, heat * 0.6)
    elx, ely = lerp(245, 330, lift), lerp(1310, 1190, lift)
    if t < 0.2:
        sx, sy = hx + 40, hy - 40
        parts.append(f'<path d="M{hx:.0f},{hy:.0f} L{sx + 30:.0f},{sy - 30:.0f}" stroke="#9aa4ae" stroke-width="14" stroke-linecap="round"/>'
                     f'<ellipse cx="{sx + 45:.0f}" cy="{sy - 48:.0f}" rx="42" ry="26" fill="#c3ccd5" stroke="#6b7680" stroke-width="5"/>')
        if t < 0.17:
            parts.append(chilli(sx + 45, sy - 70, 0.55, rot=15))
    parts.insert(len(parts) - (2 if t < 0.17 else 1 if t < 0.2 else 0), arm((290, 1150), (elx, ely), (hx, hy), arm_skin))

    # right arm and the water glass: sits on the table, then glugged
    gx, gy = lerp(900, 640, drinking), lerp(1330, 880, drinking)
    rot = lerp(0, -115, drinking)
    level = 0.8 if t < 0.62 else 0.8 - 0.75 * ((litres * 1.7) % 1) if t < 0.84 else 0.1
    parts.append(glass(gx, gy, rot, level))
    parts.append(arm((790, 1150), (lerp(880, 820, drinking), lerp(1310, 1160, drinking)),
                     (gx - lerp(45, 20, drinking), gy + lerp(60, 70, drinking)), arm_skin))
    # empty 1 L bottles pile up
    for i in range(int(litres + 1e-6)):
        parts.append(bottle(925 + i * 55, 1770))

    # Scoville meter
    fill = seg(t, 0.2, 0.45)
    top, bot = 640, 1190
    lvl = bot - (bot - top) * fill
    parts.append(f'<rect x="40" y="{top - 10}" width="70" height="{bot - top + 30}" rx="35" fill="#ffffff" stroke="#231a2e" stroke-width="7"/>'
                 f'<rect x="54" y="{lvl:.0f}" width="42" height="{bot - lvl + 20:.0f}" rx="21" fill="#e8331c"/>'
                 f'<circle cx="75" cy="{bot + 45}" r="52" fill="#e8331c" stroke="#231a2e" stroke-width="7"/>')
    for v, lab in [(0, "0"), (100 / 350, "100K"), (1, "350K")]:
        y = bot - (bot - top) * v
        parts.append(f'<path d="M110,{y:.0f} L130,{y:.0f}" stroke="#231a2e" stroke-width="5"/>' + text(138, y + 12, lab, 36, anchor="start", sw=7))
    parts.append(text(78, 600, "SCOVILLE", 40, fill="#f2c230", sw=8))
    if fill > 0.98:
        parts.append(text(170, 560, "OFF THE SCALE!", 44, fill="#e8331c", sw=8, anchor="start", extra='transform="rotate(-5 170 560)"'))

    # water counter
    parts.append(f'<rect x="690" y="40" width="360" height="92" rx="16" fill="#2f6fd0" stroke="#231a2e" stroke-width="7"/>'
                 + text(870, 106, f"WATER: {litres:.1f} L", 58, fill="#ffffff", sw=0))

    # captions
    if t < 0.2:
        cap = "Just one little chilli..."
    elif t < 0.42:
        cap = "Hmm. That's a bit warm."
    elif t < 0.84:
        cap = "SCOTCH BONNET!!!"
    else:
        cap = "Scotch bonnet 1, Dad 0"
    parts.append(f'<rect x="0" y="1760" width="1080" height="160" fill="#231a2e" opacity="0.0"/>')
    parts.append(text(540, 1880 if t >= 0.84 else 1860, cap, 92 if t >= 0.42 else 78, fill="#f2c230" if t >= 0.42 else "#ffffff", sw=14))
    if t >= 0.84:
        parts.append(text(540, 1760, "(3 litres of water later)", 44, fill="#ffffff", sw=8))

    parts.append('</svg>')
    return "".join(parts)


def render(t, scale=1.0):
    png = cairosvg.svg2png(bytestring=scene(t).encode(), output_width=int(W * scale), output_height=int(H * scale))
    return Image.open(io.BytesIO(png)).convert("RGB")


if __name__ == "__main__":
    render(0.55).save("images/chilli-still.png")
    open("images/chilli-still.svg", "w").write(scene(0.55))

    N, FPS = 150, 15
    ts = [i / (N - 1) for i in range(N)]
    hold = [1.0] * (FPS * 2)  # hold on the final score

    # GIF: half size, one shared palette (flat cartoon colours compress well)
    small = [render(t, 0.5) for t in ts + hold[:1]]
    pal = small[N // 2].quantize(colors=128)
    frames = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in small]
    durs = [1000 // FPS] * N + [2500]
    frames[0].save("images/chilli.gif", save_all=True, append_images=frames[1:], duration=durs, loop=0, optimize=True)

    # MP4: full size
    w = imageio_ffmpeg.write_frames("images/chilli.mp4", (W, H), fps=FPS, codec="libx264", quality=None,
                                    macro_block_size=8, pix_fmt_out="yuv420p",
                                    output_params=["-crf", "22", "-preset", "slow", "-movflags", "+faststart"])
    w.send(None)
    for t in ts + hold:
        w.send(np.asarray(render(t)))
    w.close()
