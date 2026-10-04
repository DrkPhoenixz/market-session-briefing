import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1400, 900
BG = "#07111f"
PANEL = "#0d1b2a"
TEXT = "#f3f7fb"
MUTED = "#9fb0c3"
BLUE = "#2788ff"
BLUE2 = "#65b5ff"
RED = "#ff3f5f"
RED2 = "#ff7a8f"
NEUTRAL = "#607286"

def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size=size)
        except OSError:
            pass
    return ImageFont.load_default()

def draw_centered(draw, xy, text, fnt, fill):
    box = draw.textbbox((0,0), text, font=fnt)
    x = xy[0] - (box[2]-box[0])/2
    y = xy[1] - (box[3]-box[1])/2
    draw.text((x,y), text, font=fnt, fill=fill)

def bias_label(v):
    if v >= 60: return "STRONG LONG"
    if v >= 20: return "LONG"
    if v > -20: return "NEUTRAL"
    if v > -60: return "SHORT"
    return "STRONG SHORT"

def draw_gauge(draw, box, title, bias):
    x0,y0,x1,y1 = box
    cx = (x0+x1)//2
    cy = y0 + 245
    r = min((x1-x0)//2 - 55, 190)
    arc_box = (cx-r, cy-r, cx+r, cy+r)

    draw.rounded_rectangle(box, radius=28, fill=PANEL)
    draw_centered(draw, (cx, y0+52), title, font(32, True), TEXT)

    # Thick 3-zone arc: LONG -> NEUTRAL -> SHORT
    draw.arc(arc_box, start=180, end=240, fill=BLUE, width=34)
    draw.arc(arc_box, start=240, end=300, fill=NEUTRAL, width=34)
    draw.arc(arc_box, start=300, end=360, fill=RED, width=34)

    # soft inner highlight
    inner = (cx-r+18, cy-r+18, cx+r-18, cy+r-18)
    draw.arc(inner, start=180, end=235, fill=BLUE2, width=8)
    draw.arc(inner, start=305, end=360, fill=RED2, width=8)

    # ticks
    for deg in range(180, 361, 15):
        a = math.radians(deg)
        rr1, rr2 = r-4, r+10
        p1 = (cx + rr1*math.cos(a), cy + rr1*math.sin(a))
        p2 = (cx + rr2*math.cos(a), cy + rr2*math.sin(a))
        draw.line((p1,p2), fill="#b7c3d1", width=2)

    # pointer: +100 LONG (left), -100 SHORT (right)
    angle = 270 - max(-100, min(100, bias))*0.9
    a = math.radians(angle)
    tip = (cx + (r-38)*math.cos(a), cy + (r-38)*math.sin(a))
    draw.line((cx,cy,tip[0],tip[1]), fill=TEXT, width=10)
    draw.ellipse((cx-16,cy-16,cx+16,cy+16), fill=TEXT)

    draw.text((x0+42, cy+30), "LONG", font=font(22,True), fill=BLUE2)
    rb = draw.textbbox((0,0),"SHORT",font=font(22,True))
    draw.text((x1-42-(rb[2]-rb[0]), cy+30), "SHORT", font=font(22,True), fill=RED2)

    label = bias_label(bias)
    col = BLUE2 if bias >= 20 else RED2 if bias <= -20 else MUTED
    draw_centered(draw, (cx, y1-68), f"{label}  {bias:+d}", font(28,True), col)

data = json.loads(Path("briefings/dashboard.json").read_text(encoding="utf-8"))

img = Image.new("RGB",(W,H),BG)
draw = ImageDraw.Draw(img)

draw.text((62,40), "The Pirates Harbor Daily", font=font(54,True), fill=TEXT)
draw.text((64,108), 'data "-scraped From social media / real human data"', font=font(22), fill=MUTED)
draw.text((64,148), data["generated_at"], font=font(20), fill="#6f849b")

cards = [
    ((55,205,685,520), "CRYPTO — SHORT TERM", int(data["crypto_st"])),
    ((715,205,1345,520), "CRYPTO — LONG TERM", int(data["crypto_lt"])),
    ((55,550,685,865), "FOREX (USD) — SHORT TERM", int(data["forex_st"])),
    ((715,550,1345,865), "FOREX (USD) — LONG TERM", int(data["forex_lt"])),
]

for box,title,bias in cards:
    draw_gauge(draw, box, title, bias)

img.save("dashboard.png", quality=95)
print("dashboard.png generated")
