"""Free 2D-animation style: every scene is a freshly drawn 2D cartoon illustration (free Pollinations image
service, no key, no cost), brought to life with camera moves (push-in, pan, gentle sway) and soft cross-fades.
If the image service fails for a scene, a Pixabay illustration and then stock footage is used instead."""
import os, random, subprocess, time, urllib.parse
import requests

FPS = 30
STYLE = ("2D animated cartoon illustration, Indian animated moral story style, clean bold outlines, flat vibrant colors, "
         "soft cel shading, expressive faces, detailed Indian background, cinematic composition, high quality, no text, no watermark")
API = "https://image.pollinations.ai/prompt/"


def _run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise RuntimeError("ffmpeg failed: " + " ".join(cmd[:4]))


def draw(query, out, w, h, seed, characters=""):
    """Ask the free image service for one 2D scene. Returns path or None."""
    prompt = f"{STYLE}. Scene: {query}." + (f" Characters: {characters}." if characters else "")
    url = API + urllib.parse.quote(prompt) + "?" + urllib.parse.urlencode(
        {"width": w, "height": h, "seed": seed, "model": "flux", "nologo": "true", "private": "true"})
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20000:
                open(out, "wb").write(r.content)
                return out
            print(f"  image service {r.status_code}, retry {attempt + 1}")
        except Exception as e:
            print(f"  image service error {e}, retry {attempt + 1}")
        time.sleep(6 + attempt * 8)
    return None


def build_scenes(chunks, w, h, work, characters="", seed0=1):
    """chunks: [(query, seconds)] -> scenes.mp4 of animated 2D illustrations."""
    import stock
    d = os.path.join(work, "a2d"); os.makedirs(d, exist_ok=True)
    # draw at a moderate size (faster, free tier friendly); ffmpeg upscales smoothly
    gw, gh = (768, 1344) if h > w else (1344, 768)
    parts, used, cache = [], set(), {}
    t0 = time.time()
    for i, (query, dur) in enumerate(chunks):
        img = os.path.join(d, f"{i:03d}.jpg")
        got = draw(query, img, gw, gh, seed0 * 1000 + i, characters)
        if not got:
            print(f"::warning::2D image failed for scene {i + 1}, using an illustration")
            got = stock.illustration(query, img, landscape=w > h, used=used)
        if not got:
            _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                  f"gradients=s={gw}x{gh}:c0=0x2b5876:c1=0x4e4376", "-frames:v", "1", img])
        cache[query] = img
        out = os.path.join(work, f"a2d{i:03d}.mp4")
        frames = max(2, int((dur + 0.5) * FPS))   # +0.5 s overlap for the cross-fade
        move = i % 5
        z = {0: f"1.0+0.12*on/{frames}", 1: f"1.12-0.12*on/{frames}", 2: "1.10", 3: "1.10", 4: f"1.05+0.08*on/{frames}"}[move]
        x = {0: "iw/2-(iw/zoom/2)", 1: "iw/2-(iw/zoom/2)", 2: f"(iw-iw/zoom)*on/{frames}",
             3: f"(iw-iw/zoom)*(1-on/{frames})", 4: "iw/2-(iw/zoom/2)+sin(on/18)*6"}[move]
        y = {0: "ih/2-(ih/zoom/2)", 1: "ih/2-(ih/zoom/2)", 2: "ih/2-(ih/zoom/2)", 3: "ih/2-(ih/zoom/2)",
             4: "ih/2-(ih/zoom/2)+cos(on/22)*5"}[move]
        vf = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
              f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={FPS},"
              f"eq=saturation=1.08:contrast=1.03,vignette=PI/6,format=yuv420p")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(frames),
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])
        parts.append((out, frames / FPS))
        print(f"  2D scene {i + 1}/{len(chunks)}  ({time.time() - t0:.0f}s)")
    # join: soft 0.5 s cross-fades in groups of 20 scenes (one ffmpeg call each), groups joined by plain concat
    groups, k = [], 0
    for g0 in range(0, len(parts), 20):
        grp = parts[g0:g0 + 20]
        gout = os.path.join(work, f"grp{k:03d}.mp4"); k += 1
        if len(grp) == 1:
            os.replace(grp[0][0], gout)
        else:
            cmd = ["ffmpeg", "-y", "-loglevel", "error"]
            for p, _ in grp:
                cmd += ["-i", p]
            fc, prev, off = [], "[0:v]", 0.0
            for j in range(1, len(grp)):
                off += grp[j - 1][1] - 0.5
                lab = f"[x{j}]"
                fc.append(f"{prev}[{j}:v]xfade=transition=fade:duration=0.5:offset={off:.3f}{lab}")
                prev = lab
            cmd += ["-filter_complex", ";".join(fc), "-map", prev, "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", gout]
            _run(cmd)
        groups.append(gout)
    if len(groups) == 1:
        os.replace(groups[0], os.path.join(work, "scenes.mp4"))
    else:
        open(os.path.join(work, "glist.txt"), "w").write("\n".join(f"file '{os.path.basename(g)}'" for g in groups))
        _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "glist.txt", "-c", "copy",
              "scenes.mp4"], cwd=work)
    return os.path.join(work, "scenes.mp4")
