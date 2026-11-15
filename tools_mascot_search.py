"""Find free 3D-cartoon character portraits on Pixabay (free for commercial use) and make a numbered contact sheet."""
import os, io, requests
from PIL import Image, ImageDraw, ImageFont
key = os.environ["PIXABAY_API_KEY"]
qs = ["3d cartoon man portrait", "3d character boy face", "3d cartoon indian man", "3d render cartoon young man",
      "3d cartoon businessman", "3d cartoon teacher", "3d cartoon girl portrait", "3d cartoon grandfather"]
seen, picks = set(), []
for q in qs:
    r = requests.get("https://pixabay.com/api/", params={"key": key, "q": q, "image_type": "illustration", "per_page": 20, "safesearch": "true"}, timeout=30).json()
    for h in r.get("hits", [])[:6]:
        if h["id"] in seen: continue
        seen.add(h["id"]); picks.append((q, h))
picks = picks[:40]
thumbs = []
for i, (q, h) in enumerate(picks):
    im = Image.open(io.BytesIO(requests.get(h["webformatURL"], timeout=30).content)).convert("RGB")
    im.thumbnail((300, 300)); c = Image.new("RGB", (300, 330), "white"); c.paste(im, ((300 - im.width) // 2, 0))
    ImageDraw.Draw(c).text((8, 305), f"{i+1}  id {h['id']}", fill="black")
    thumbs.append(c)
    open("mascot_candidates.txt", "a").write(f"{i+1} {h['id']} {h['largeImageURL']} {q}\n")
cols = 8; rows = (len(thumbs) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 300, rows * 330), "white")
for i, t in enumerate(thumbs):
    sheet.paste(t, ((i % cols) * 300, (i // cols) * 330))
sheet.save("mascots.jpg", quality=85)
print(len(thumbs))
