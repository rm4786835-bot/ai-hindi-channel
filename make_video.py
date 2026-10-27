r"""
Free AI Hindi video maker — no credits needed.
Voice: Microsoft Edge neural voice (free) via edge-tts.
Video: background + Hindi captions rendered by FFmpeg (libass), so Hindi matras render correctly.

Usage:
    python make_video.py scripts\day01.txt            -> long video (16:9)
    python make_video.py scripts\day01_short.txt --short   -> YouTube Short (9:16)

Script format (plain .txt, UTF-8):
    # Section title          <- a line starting with "# " starts a new section (shown top-left)
    Sentences of voiceover...  (every sentence becomes one caption screen)
"""
import argparse, asyncio, hashlib, os, re, shutil, subprocess, sys

VOICE = "hi-IN-SwaraNeural"      # Hindi female. Male option: hi-IN-MadhurNeural
EN_VOICE = "en-IN-NeerjaNeural"  # lines starting with "EN:" are spoken in Indian-English female voice
RATE = "+5%"                     # speed: "+0%" normal, "+10%" faster
CHANNEL = "AI Hindi"             # watermark text, top-right
GAP = 0.25                       # seconds of silence between sentences


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-2000:])
        sys.exit("FFmpeg step failed: " + " ".join(cmd[:3]))
    return r.stdout


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())


def parse(path, default_query="city life"):
    sec, items, query = "", [], default_query
    for raw in open(path, encoding="utf-8-sig").read().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            sec = line[2:].strip()
            continue
        if line.startswith("@"):
            query = line[1:].strip() or default_query
            continue
        en = line.startswith("EN:")
        if en:
            line = line[3:].strip()
        for s in re.split(r"(?<=[।?!.])\s+" if en else r"(?<=[।?!])\s+", line):
            if s.strip():
                items.append((sec, ("\x01" if en else "") + s.strip(), query))
    if not items:
        sys.exit("Script is empty.")
    return items


async def tts(text, out, voice=None):
    import edge_tts
    await edge_tts.Communicate(text, voice or VOICE, rate=RATE if voice in (None, VOICE) else "-5%").save(out)


def fake_tts(text, out):  # for testing without internet
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", f"{0.07 * len(text) + 0.5:.2f}", "-c:a", "libmp3lame", out])


def make_bg(w, h, out):
    from PIL import Image, ImageDraw
    a, b = (11, 20, 48), (20, 34, 78)
    im = Image.new("RGB", (w, h)); d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
    s = 1 if h > w else w / 1920
    d.rounded_rectangle([int(90 * s), int(72 * s), int(104 * s), int(128 * s)], radius=4, fill=(255, 212, 59))
    im.save(out)


def ass_time(t):
    cs = int(round(t * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def color_words(text):
    out = []
    for w in text.split():
        w = w.replace("{", "(").replace("}", ")")
        out.append("{\\c&H3BD4FF&}" + w + "{\\c&HFFF4F0&}" if re.search(r"[A-Za-z]", w) else w)
    return " ".join(out)


def write_ass(items, times, w, h, font, short, out, footage=False):
    s = w / 1920 if not short else 1
    body = 112 if short else 92
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Main,{font},{body},&H00FFF4F0,&H00FFF4F0,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,{5 if footage else 0},{2 if footage else 0},5,{150 if not short else 90},{150 if not short else 90},0,1",
        f"Style: Head,{font},{int(52*s) if not short else 56},&H00FFF4F0,&H00FFF4F0,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,{3 if footage else 0},0,7,{int(125*s) if not short else 125},40,{int(66*s) if not short else 66},1",
        f"Style: Mark,{font},{int(38*s) if not short else 40},&H00E6D2C8,&H00E6D2C8,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,{2 if footage else 0},0,9,40,{int(90*s) if not short else 90},{int(80*s) if not short else 80},1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    total = times[-1][1]
    lines.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Mark,,0,0,0,,{CHANNEL}")
    for (sec, text, _q), (a, b) in zip(items, times):
        size = body if len(text) < 70 else int(body * 0.88) if len(text) < 120 else int(body * 0.76)
        if text.startswith("\x01"):
            text = text[1:]
            body_txt = "{\\c&H3BD4FF&}" + text.replace("{", "(").replace("}", ")")
        else:
            body_txt = color_words(text)
        lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Main,,0,0,0,,{{\\fs{size}\\fad(120,80)}}{body_txt}")
        if sec:
            lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Head,,0,0,0,,{sec}")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--short", action="store_true", help="vertical 9:16 Short")
    ap.add_argument("--font", default="Nirmala UI", help="Hindi font name installed on the PC")
    ap.add_argument("--test", action="store_true", help="silent test run without internet")
    ap.add_argument("--brand", default=None, help="watermark text (channel name)")
    ap.add_argument("--default-query", default="city life", help="stock footage search words when the script has no @ line")
    ap.add_argument("--plain", action="store_true", help="force the plain gradient background")
    ap.add_argument("--voice", default=None, help="Hindi narrator voice, e.g. hi-IN-MadhurNeural for stories")
    a = ap.parse_args()
    global CHANNEL, VOICE
    if a.voice:
        VOICE = a.voice
    if a.brand:
        CHANNEL = a.brand

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found. Install it first (see README).")

    name = os.path.splitext(os.path.basename(a.script))[0]
    work = os.path.abspath(os.path.join("build", name)); os.makedirs(work, exist_ok=True)
    w, h = (1080, 1920) if a.short else (1920, 1080)
    items = parse(a.script, a.default_query)
    print(f"{len(items)} sentences. Making voice...")

    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP), "-c:a", "libmp3lame", "gap.mp3"], cwd=work)
    alist, times, t = [], [], 0.0
    for i, (_, raw, _q) in enumerate(items):
        voice = EN_VOICE if raw.startswith("\x01") else VOICE
        text = raw.lstrip("\x01")
        key = hashlib.md5(f"{voice}|{RATE}|{text}".encode("utf-8")).hexdigest()[:10]
        fn = f"v_{key}.mp3"; p = os.path.join(work, fn)
        if not os.path.exists(p) or a.test:
            if a.test:
                fake_tts(text, p)
            else:
                for attempt in range(3):
                    try:
                        asyncio.run(tts(text, p, voice)); break
                    except Exception as e:
                        if attempt == 2:
                            sys.exit(f"Voice failed on sentence {i+1}: {e}")
        d = duration(p)
        times.append((t, t + d + GAP)); t += d + GAP
        alist += [f"file '{fn}'", "file 'gap.mp3'"]
        print(f"  {i+1}/{len(items)}", end="\r")
    open(os.path.join(work, "alist.txt"), "w", encoding="utf-8").write("\n".join(alist))
    print("\nJoining voice...")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "alist.txt", "-c:a", "aac", "-b:a", "160k", "voice.m4a"], cwd=work)

    import stock
    footage = (stock.enabled() or os.environ.get("STOCK_TEST")) and not a.plain
    fontsdir = f":fontsdir={os.environ['FONTS_DIR']}" if os.environ.get("FONTS_DIR") else ""
    write_ass(items, times, w, h, a.font, a.short, os.path.join(work, "subs.ass"), footage=bool(footage))
    out_name = f"{name}.mp4"
    if footage:
        # cut footage at sentence ends, a new clip roughly every 5-8 seconds or when the topic (@ query) changes
        chunks, cur_q, cur_d = [], None, 0.0
        for (_, _, q), (st, en) in zip(items, times):
            d = en - st
            if cur_q is not None and (q != cur_q or cur_d >= 5.0):
                chunks.append((cur_q, cur_d)); cur_d = 0.0
            cur_q = q; cur_d += d
        chunks.append((cur_q, cur_d))
        print(f"Fetching footage for {len(chunks)} scenes...")
        foot = stock.build_footage(chunks, w, h, work, test=bool(os.environ.get("STOCK_TEST")))
        stock.make_music(os.path.join(work, "music.wav"), seed=len(name))
        print("Rendering video...")
        run(["ffmpeg", "-y", "-i", "footage.mp4", "-i", "voice.m4a", "-stream_loop", "-1", "-i", "music.wav",
             "-filter_complex",
             f"[0:v]ass=subs.ass{fontsdir}[v];[2:a]volume=0.13,afade=t=in:d=2,afade=t=out:st={max(0, t - 3):.2f}:d=3[m];"
             f"[1:a][m]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{t:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out_name], cwd=work)
    else:
        make_bg(w, h, os.path.join(work, "bg.png"))
        print("Rendering video...")
        run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", "bg.png", "-i", "voice.m4a",
             "-vf", "ass=subs.ass" + fontsdir, "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "22",
             "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", out_name], cwd=work)
    os.makedirs("output", exist_ok=True)
    final = os.path.abspath(os.path.join("output", out_name))
    shutil.move(os.path.join(work, out_name), final)
    chap, last = [], None
    for (sec, _, _q), (st, _) in zip(items, times):
        if sec and sec != last:
            mm, ss = divmod(int(st), 60); chap.append(f"{mm}:{ss:02d} {sec}"); last = sec
    if chap and not a.short:
        chap[0] = "0:00" + chap[0][chap[0].index(" "):]
        open(os.path.join("output", f"{name}_chapters.txt"), "w", encoding="utf-8").write("\n".join(chap) + "\n")
        print("Chapters for description:\n" + "\n".join(chap))
    m, s = divmod(int(t), 60)
    print(f"Done: {final}  ({m}:{s:02d})")


if __name__ == "__main__":
    main()
