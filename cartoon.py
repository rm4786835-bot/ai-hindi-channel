"""Free 2D cartoon style.

* Scene backgrounds: cartoon / flat illustrations from Pixabay (image_type=illustration), slow pan & zoom.
* A cartoon narrator character drawn in code (no copyrighted art) whose mouth opens and closes with the
  loudness of the voice, frame by frame, and who blinks — so the mouth matches the speech.
"""
import math, os, random, struct, subprocess, wave
from PIL import Image, ImageDraw

FPS = 30
MOUTHS = 4  # 0 closed .. 3 wide open


def _run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise RuntimeError("ffmpeg failed: " + " ".join(cmd[:4]))
    return r.stdout


# ---------------------------------------------------------------- character
CHARS = {
    # skin, hair, shirt, accent
    "narrator": ((241, 194, 150), (40, 30, 30), (230, 120, 40), (255, 212, 59)),   # young storyteller, orange kurta
    "dadi":     ((228, 178, 140), (225, 225, 230), (150, 60, 110), (255, 212, 59)),  # grandmother, white hair, purple saree
    "teacher":  ((236, 188, 146), (35, 30, 35), (40, 110, 190), (255, 255, 255)),    # blue shirt
}


def draw_character(path, mouth, blink, kind="narrator", size=520):
    skin, hair, shirt, acc = CHARS.get(kind, CHARS["narrator"])
    S = size * 2  # supersample for smooth edges
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = (20, 20, 30, 255)
    lw = int(S * 0.012)
    cx = S // 2
    # body
    d.rounded_rectangle([cx - S * .30, S * .66, cx + S * .30, S * 1.05], radius=int(S * .14), fill=shirt + (255,), outline=o, width=lw)
    d.polygon([(cx - S * .07, S * .66), (cx, S * .76), (cx + S * .07, S * .66)], fill=acc + (255,), outline=o)
    # neck
    d.rectangle([cx - S * .06, S * .56, cx + S * .06, S * .68], fill=skin + (255,), outline=o, width=lw)
    # hair back
    if kind == "dadi":
        d.ellipse([cx - S * .27, S * .06, cx + S * .27, S * .52], fill=hair + (255,), outline=o, width=lw)
        d.ellipse([cx - S * .10, S * .00, cx + S * .10, S * .16], fill=hair + (255,), outline=o, width=lw)  # bun
    else:
        d.ellipse([cx - S * .27, S * .08, cx + S * .27, S * .50], fill=hair + (255,), outline=o, width=lw)
    # ears
    for sx in (-1, 1):
        d.ellipse([cx + sx * S * .25 - S * .05, S * .30, cx + sx * S * .25 + S * .05, S * .42], fill=skin + (255,), outline=o, width=lw)
    # face
    d.ellipse([cx - S * .24, S * .13, cx + S * .24, S * .60], fill=skin + (255,), outline=o, width=lw)
    # front hair
    if kind == "dadi":
        d.chord([cx - S * .24, S * .10, cx + S * .24, S * .40], 190, 350, fill=hair + (255,), outline=o, width=lw)
    else:
        d.chord([cx - S * .25, S * .07, cx + S * .25, S * .38], 180, 360, fill=hair + (255,), outline=o, width=lw)
        d.polygon([(cx - S * .05, S * .14), (cx + S * .18, S * .14), (cx + S * .02, S * .26)], fill=hair + (255,))
    # eyes
    ey = S * .36
    for sx in (-1, 1):
        ex = cx + sx * S * .095
        if blink:
            d.line([ex - S * .04, ey, ex + S * .04, ey], fill=o, width=int(lw * 1.4))
        else:
            d.ellipse([ex - S * .045, ey - S * .045, ex + S * .045, ey + S * .045], fill=(255, 255, 255, 255), outline=o, width=lw)
            d.ellipse([ex - S * .022, ey - S * .02, ex + S * .022, ey + S * .025], fill=(30, 25, 25, 255))
            d.ellipse([ex - S * .006, ey - S * .012, ex + S * .008, ey + S * .002], fill=(255, 255, 255, 255))
        d.arc([ex - S * .05, ey - S * .10, ex + S * .05, ey - S * .03], 200, 340, fill=o, width=lw)  # brows
    if kind == "dadi":  # spectacles
        for sx in (-1, 1):
            ex = cx + sx * S * .095
            d.ellipse([ex - S * .065, ey - S * .06, ex + S * .065, ey + S * .06], outline=(90, 60, 30, 255), width=lw)
        d.line([cx - S * .03, ey, cx + S * .03, ey], fill=(90, 60, 30, 255), width=lw)
    # nose & cheeks
    d.arc([cx - S * .03, S * .38, cx + S * .03, S * .45], 20, 160, fill=o, width=lw)
    for sx in (-1, 1):
        d.ellipse([cx + sx * S * .15 - S * .035, S * .44, cx + sx * S * .15 + S * .035, S * .48], fill=(240, 140, 140, 150))
    if kind == "narrator":  # small tilak-free bindi-free neutral; add moustache for variety
        pass
    # mouth
    my = S * .50
    mw = S * (.075 + .012 * mouth)
    if mouth == 0:
        d.arc([cx - mw, my - S * .04, cx + mw, my + S * .02], 20, 160, fill=o, width=int(lw * 1.2))
    else:
        mh = S * (.018 + .022 * mouth)
        d.ellipse([cx - mw, my - mh * .6, cx + mw, my + mh], fill=(120, 30, 40, 255), outline=o, width=lw)
        d.ellipse([cx - mw * .55, my + mh * .1, cx + mw * .55, my + mh * .9], fill=(235, 110, 120, 255))  # tongue
        d.chord([cx - mw * .85, my - mh * .6, cx + mw * .85, my + mh * .1], 180, 360, fill=(255, 255, 255, 255))  # teeth
    im = im.resize((size, size), Image.LANCZOS)
    im.save(path)


def mouth_track(voice_path, work):
    """Return a list (one value per video frame) of mouth openness 0..3 from voice loudness."""
    wav = os.path.join(work, "voice_mono.wav")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", voice_path, "-ac", "1", "-ar", "16000", wav])
    with wave.open(wav) as wf:
        n = wf.getnframes(); sr = wf.getframerate(); raw = wf.readframes(n)
    samples = struct.unpack("<%dh" % (len(raw) // 2), raw)
    hop = sr // FPS
    rms = []
    for i in range(0, len(samples), hop):
        seg = samples[i:i + hop]
        rms.append(math.sqrt(sum(s * s for s in seg) / max(1, len(seg))) if seg else 0)
    peak = sorted(rms)[int(len(rms) * .95)] if rms else 1
    out, prev = [], 0
    for v in rms:
        x = v / (peak or 1)
        m = 0 if x < .10 else 1 if x < .30 else 2 if x < .60 else 3
        if abs(m - prev) > 1:  # smooth jumps
            m = prev + (1 if m > prev else -1)
        out.append(m); prev = m
    return out


def character_track(voice_path, work, kind, size):
    """Builds avatar.mov (transparent) whose mouth follows the voice; returns its path."""
    adir = os.path.join(work, "avatar"); os.makedirs(adir, exist_ok=True)
    for m in range(MOUTHS):
        for b in (0, 1):
            draw_character(os.path.join(adir, f"m{m}b{b}.png"), m, b, kind, size)
    track = mouth_track(voice_path, work)
    rnd = random.Random(7)
    blink_frames = set()
    f = rnd.randint(60, 120)
    while f < len(track):
        blink_frames.update({f, f + 1, f + 2}); f += rnd.randint(70, 160)
    lines, cur, run_len = [], None, 0
    for i, m in enumerate(track):
        key = f"m{m}b{1 if i in blink_frames else 0}.png"
        if key == cur:
            run_len += 1
        else:
            if cur:
                lines += [f"file 'avatar/{cur}'", f"duration {run_len / FPS:.4f}"]
            cur, run_len = key, 1
    lines += [f"file 'avatar/{cur}'", f"duration {run_len / FPS:.4f}", f"file 'avatar/{cur}'"]
    open(os.path.join(work, "avatar.txt"), "w").write("\n".join(lines))
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "avatar.txt",
          "-vf", f"fps={FPS},format=rgba", "-c:v", "qtrle", "avatar.mov"], cwd=work)
    return os.path.join(work, "avatar.mov")


# ---------------------------------------------------------------- scenes
def build_scenes(chunks, w, h, work, test=False):
    """chunks: [(query, seconds)] -> scenes.mp4 made of cartoon illustrations with slow pan/zoom."""
    import stock
    os.makedirs(os.path.join(work, "ill"), exist_ok=True)
    parts, used = [], set()
    for i, (query, dur) in enumerate(chunks):
        img = os.path.join(work, "ill", f"{i:03d}.png")
        got = None
        if not test:
            got = stock.illustration(query, img, landscape=w > h, used=used)
        if not got:
            hue = (abs(hash(query)) + i * 37) % 360
            _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                  f"gradients=s=1280x720:c0=0x4a90e2:c1=0xf5d76e:x0=0:y0=0:x1=1280:y1=720,hue=h={hue}", "-frames:v", "1", img])
        out = os.path.join(work, f"sc{i:03d}.mp4")
        frames = max(1, int(dur * FPS))
        direction = i % 4
        zx = ["iw/2-(iw/zoom/2)", "0", "iw-iw/zoom", "iw/2-(iw/zoom/2)"][direction]
        zy = ["ih/2-(ih/zoom/2)", "ih/2-(ih/zoom/2)", "ih/2-(ih/zoom/2)", "0"][direction]
        vf = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
              f"zoompan=z='min(1.0+0.10*on/{frames},1.10)':x='{zx}':y='{zy}':d={frames}:s={w}x{h}:fps={FPS},"
              f"eq=saturation=1.15,format=yuv420p")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(frames),
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", out])
        parts.append(out)
        print(f"  scene {i + 1}/{len(chunks)}", end="\r")
    open(os.path.join(work, "slist.txt"), "w").write("\n".join(f"file '{os.path.basename(p)}'" for p in parts))
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "slist.txt", "-c", "copy", "scenes.mp4"], cwd=work)
    print()
    return os.path.join(work, "scenes.mp4")
