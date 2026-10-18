"""Generate original North Jersey skyline + bridge icon for The Sitdown BBS."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((28, 28, 996, 996), radius=210, fill="#0C1318", outline="#59646B", width=12)
# Night-sky gradient, clipped within the rounded app tile.
for y in range(80, 900):
    t = (y - 80) / 820
    col = (int(9 + 32*t), int(22 + 8*t), int(31 + 8*t), 255)
    d.line((75, y, 949, y), fill=col, width=1)
# Distant skyline, original simplified silhouette.
buildings = [(105,470,175,690),(183,415,245,690),(255,505,312,690),
             (325,365,390,690),(398,450,460,690),(473,405,520,690),
             (533,480,595,690),(612,340,677,690),(693,440,745,690),
             (756,375,820,690),(830,490,918,690)]
for x1,y1,x2,y2 in buildings:
    d.rectangle((x1,y1,x2,y2),fill="#050B10")
    for x in range(x1+11,x2-4,16):
        for y in range(y1+15,680,25):
            if ((x*7+y*3)//11)%5 != 0:
                d.rectangle((x,y,x+4,y+7),fill="#E4A75A")
# Bridge suspension cables and towers.
for x in (225, 795):
    d.rectangle((x-15,305,x+15,695),fill="#C8C8BD")
    d.rectangle((x-25,305,x+25,325),fill="#E7E3D7")
d.line([(95,520),(225,335),(510,500),(795,335),(930,520)],fill="#DAD9D1",width=13,joint="curve")
d.line((85,685,945,685),fill="#F4B942",width=20)
for x in range(115,920,35):
    d.line((x,685,x,520+int(120*abs(math.sin(x/175)))),fill="#64747B",width=4)
# Italian tricolor stripes, subtle beneath the bridge.
for i,color in enumerate(("#008C45","#F5F5F0","#C62828")):
    d.rectangle((95+i*280,744,95+(i+1)*280,780),fill=color)
# Original simplified New Jersey silhouette with the tricolor.
mask = Image.new('L', (S, S), 0)
md = ImageDraw.Draw(mask)
md.polygon([(545,245),(650,290),(622,360),(655,425),(612,510),(573,575),
            (543,650),(488,692),(455,653),(473,605),(438,557),(462,495),
            (493,444),(478,385),(510,340),(515,283)], fill=255)
flag = Image.new('RGBA', (S, S), '#F5F5F0')
fd = ImageDraw.Draw(flag)
fd.rectangle((0,0,510,S), fill='#008C45')
fd.rectangle((575,0,S,S), fill='#C62828')
img.paste(flag, (0,0), mask)
d = ImageDraw.Draw(img)
# Big recognizable BBS monogram with contrast for Dock sizes.
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 110)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 60)
except OSError:
    font = ImageFont.load_default()
    small = font
d.rounded_rectangle((170,790,854,924),radius=35,fill="#111518",outline="#C62828",width=8)
d.text((512,852),"BBS",font=font,anchor="mm",fill="#F5F5F0",stroke_width=5,stroke_fill="#C62828")
d.text((512,185),"THE SITDOWN",font=small,anchor="mm",fill="#F5F5F0",stroke_width=2,stroke_fill="#05090C")
out=Path("build")
out.mkdir(exist_ok=True)
# Clip all artwork to the rounded tile silhouette.
alpha = Image.new('L', (S, S), 0)
ImageDraw.Draw(alpha).rounded_rectangle((28,28,996,996), radius=210, fill=255)
img.putalpha(alpha)
img.save(out/"sitdown-icon.png")

preview = Path("docs/images/app-icon.png")
preview.parent.mkdir(parents=True, exist_ok=True)
img.save(preview)
