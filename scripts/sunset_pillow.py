from PIL import Image, ImageDraw, ImageFont
import math, random
W, H = 1080, 1920  # phone portrait
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img)
# sunset gradient sky
top, bot = (20, 24, 82), (255, 140, 90)
for y in range(H):
    t = min(1, y / (H * 0.62))
    d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i]-top[i])*t) for i in range(3)))
random.seed(7)
for _ in range(160):
    x, y = random.randint(0, W), random.randint(0, int(H*0.35))
    r = random.choice([1, 1, 2, 3])
    d.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 230))
# sun
cx, cy = W//2, int(H*0.60)
for r in range(260, 180, -4):
    a = (260 - r) / 80
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, int(150+60*a), int(90+30*a)))
# mountains
def ridge(base, amp, color, seed):
    random.seed(seed); pts = [(0, H)]
    for x in range(0, W+40, 40):
        pts.append((x, base - amp*abs(math.sin(x/170 + seed)) - random.randint(0, 40)))
    pts.append((W, H)); d.polygon(pts, fill=color)
ridge(int(H*0.66), 220, (92, 52, 110), 1)
ridge(int(H*0.74), 160, (58, 34, 80), 3)
ridge(int(H*0.83), 110, (30, 20, 50), 5)
# text
try:
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
    s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
except OSError:
    f = s = ImageFont.load_default()
for text, font, y in [("Hello from Claude", f, 1690), ("made in a cloud container", s, 1790)]:
    w = d.textlength(text, font=font)
    d.text(((W-w)/2, y), text, font=font, fill=(255, 235, 215))
img.save("images/sunset.png")
