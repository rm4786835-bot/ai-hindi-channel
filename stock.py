"""Free real-footage backgrounds from Pixabay or Pexels (free APIs, footage free for commercial use) + generated background music.

Script lines starting with "@ " set the English search words for the following sentences, e.g.
    @ young student studying laptop
If neither PIXABAY_API_KEY nor PEXELS_API_KEY is set, callers fall back to the plain background.
"""
import json, math, os, random, struct, subprocess, sys, wave

API = "https://api.pexels.com"


def _run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise RuntimeError("ffmpeg failed: " + " ".join(cmd[:4]))
    return r.stdout


def provider():
    if os.environ.get("PIXABAY_API_KEY", "").strip():
        return "pixabay"
    if os.environ.get("PEXELS_API_KEY", "").strip():
        return "pexels"
    return None


def enabled():
    return provider() is not None


def _pixabay(path, params):
    import requests
    params = dict(params, key=os.environ["PIXABAY_API_KEY"].strip(), safesearch="true")
    params["q"] = params.get("q", "")[:95]
    for attempt in range(3):
        try:
            r = requests.get("https://pixabay.com/api/" + path, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            print(f"pixabay {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print("pixabay error:", e)
    return {}


def _video_candidates(q, portrait, used):
    """Returns [(id, url)] of suitable clips for a search phrase from the active provider."""
    out = []
    if provider() == "pixabay":
        data = _pixabay("videos/", {"q": q, "per_page": 30, "video_type": "film"})
        for v in data.get("hits", []):
            if v["id"] in used or v.get("duration", 0) < 4:
                continue
            best = None
            for size in ("large", "medium", "small"):
                f = (v.get("videos") or {}).get(size) or {}
                if not f.get("url") or not f.get("width"):
                    continue
                side = f["width"] if portrait else f["height"]
                if 700 <= side <= 2200 and (best is None or abs(side - 1080) < abs(best[0] - 1080)):
                    best = (side, f["url"])
            if best:
                out.append((v["id"], best[1]))
    else:
        data = _get("/videos/search", {"query": q, "per_page": 20, "size": "medium",
                                      "orientation": "portrait" if portrait else "landscape"})
        for v in data.get("videos", []):
            if v["id"] in used or v.get("duration", 0) < 4:
                continue
            best = None
            for f in v.get("video_files", []):
                if f.get("file_type") != "video/mp4" or not f.get("width") or not f.get("height"):
                    continue
                side = f["width"] if portrait else f["height"]
                if 700 <= side <= 1920 and (best is None or abs(side - 1080) < abs(best[0] - 1080)):
                    best = (side, f["link"])
            if best:
                out.append((v["id"], best[1]))
    return out


def _get(path, params):
    import requests
    for attempt in range(3):
        try:
            r = requests.get(API + path, params=params, timeout=30,
                             headers={"Authorization": os.environ["PEXELS_API_KEY"].strip()})
            if r.status_code == 200:
                return r.json()
            print(f"pexels {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print("pexels error:", e)
    return {}


def _download(url, out):
    import requests
    if os.path.exists(out) and os.path.getsize(out) > 10000:
        return out
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return out


class ClipPool:
    """Gives a different footage clip for every call, per search query."""

    def __init__(self, work, portrait, test=False):
        self.work, self.portrait, self.test = work, portrait, test
        self.cache, self.pos, self.used = {}, {}, set()
        os.makedirs(os.path.join(work, "clips"), exist_ok=True)

    def _search(self, query):
        if query in self.cache:
            return self.cache[query]
        files = []
        if self.test:
            files = [("test", i) for i in range(6)]
        else:
            for q in (query, " ".join(query.split()[:2]), query.split()[0] if query.split() else "city"):
                files += [f for f in _video_candidates(q, self.portrait, self.used) if f not in files]
                if len(files) >= 4:
                    break
            random.Random(query).shuffle(files)
        self.cache[query] = files
        self.pos[query] = 0
        return files

    def next(self, query):
        key = query
        files = self._search(key)
        if not files:
            key = "city life"
            files = self._search(key)
        if not files:
            return None
        for _ in range(len(files)):
            vid, link = files[self.pos[key] % len(files)]
            self.pos[key] += 1
            name = f"t{abs(hash(key)) % 9999}_{link}.mp4" if self.test else f"{vid}.mp4"
            out = os.path.join(self.work, "clips", name)
            try:
                if self.test:
                    hue = (abs(hash(key)) + link * 40) % 360
                    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                          f"testsrc2=s=640x360:d=5,hue=h={hue}", "-c:v", "libx264", "-preset", "ultrafast", out])
                else:
                    _download(link, out)
                self.used.add(vid)
                return out
            except Exception as ex:
                print("clip download failed:", ex)
        return None


def build_footage(chunks, w, h, work, test=False):
    """chunks: list of (query, seconds). Returns path of a silent footage video exactly sum(seconds) long."""
    pool = ClipPool(work, portrait=h > w, test=test)
    parts = []
    for i, (query, dur) in enumerate(chunks):
        src = pool.next(query)
        out = os.path.join(work, f"seg{i:03d}.mp4")
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30,"
              f"eq=brightness=-0.06:saturation=1.08,"
              f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.38:t=fill,format=yuv420p")
        if src:
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", src, "-t", f"{dur:.3f}",
                   "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out]
        else:
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x0b1430:s={w}x{h}:r=30",
                   "-t", f"{dur:.3f}", "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", out]
        _run(cmd)
        parts.append(out)
        print(f"  footage {i + 1}/{len(chunks)}", end="\r")
    lst = os.path.join(work, "flist.txt")
    open(lst, "w").write("\n".join(f"file '{os.path.basename(p)}'" for p in parts))
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "flist.txt", "-c", "copy", "footage.mp4"], cwd=work)
    print()
    return os.path.join(work, "footage.mp4")


def make_music(out, seed=0, seconds=16.0):
    """Soft, copyright-free ambient pad loop (16 s, 4 chords) generated from math. Loop it with ffmpeg."""
    sr = 22050
    rnd = random.Random(seed)
    progressions = [
        [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)],   # Am F C G
        [(48, 52, 55), (55, 59, 62), (57, 60, 64), (53, 57, 60)],   # C G Am F
        [(50, 53, 57), (55, 59, 62), (48, 52, 55), (57, 60, 64)],   # Dm G C Am
    ]
    prog = progressions[rnd.randrange(len(progressions))]
    chord_len = 4.0
    n = int(seconds * sr)
    frames = bytearray()
    for i in range(n):
        t = i / sr
        ci = int(t // chord_len) % len(prog)
        local = t % chord_len
        env = min(1.0, local / 0.8) * min(1.0, (chord_len - local) / 0.8)
        s = 0.0
        for k, note in enumerate(prog[ci]):
            f = 440.0 * 2 ** ((note - 69) / 12)
            s += math.sin(2 * math.pi * f * t + k) * 0.22 + math.sin(2 * math.pi * f * 2 * t) * 0.04
        bass = math.sin(2 * math.pi * (440.0 * 2 ** ((prog[ci][0] - 12 - 69) / 12)) * t) * 0.25
        trem = 0.85 + 0.15 * math.sin(2 * math.pi * 0.25 * t)
        v = (s + bass) * env * trem * 0.35
        frames += struct.pack("<h", int(max(-1, min(1, v)) * 32767))
    with wave.open(out, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(bytes(frames))
    return out


def photo(query, out, landscape=True):
    if provider() == "pixabay":
        hits = _pixabay("", {"q": query, "image_type": "photo", "per_page": 20,
                             "orientation": "horizontal" if landscape else "vertical"}).get("hits", [])
        if not hits:
            return None
        p = hits[random.Random(query).randrange(min(len(hits), 8))]
        return _download(p.get("largeImageURL") or p["webformatURL"], out)
    data = _get("/v1/search", {"query": query, "per_page": 10, "orientation": "landscape" if landscape else "portrait"})
    photos = data.get("photos", [])
    if not photos:
        return None
    p = photos[random.Random(query).randrange(len(photos))]
    return _download(p["src"].get("large2x") or p["src"]["large"], out)
