import sys
from pathlib import Path
from PIL import Image
pngs = sorted(Path(sys.argv[1]).glob("page*.png"))
ims = [Image.open(p) for p in pngs]
w, h = ims[0].size
cols = 2
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w + (cols + 1) * 8, rows * h + (rows + 1) * 8), "#888888")
for i, im in enumerate(ims):
    sheet.paste(im, (8 + (i % cols) * (w + 8), 8 + (i // cols) * (h + 8)))
sheet.save(sys.argv[2])
print(sheet.size)
