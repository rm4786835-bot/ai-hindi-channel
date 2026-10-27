"""Builds every day in scripts/ that has no GitHub release yet.
For dayNN it makes: dayNN.mp4 (long), dayNN_short.mp4 (if script exists), dayNN_thumb.jpg,
dayNN_description.txt (chapters filled in), and publishes them as release "dayNN"."""
import glob, json, os, subprocess, sys

FONT = os.environ.get("FONT", "Noto Sans Devanagari")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
TEST = "--test" in sys.argv
DEFAULT_QUERY = {"tech": "technology laptop", "english": "people talking conversation", "money": "money finance", "action": "dark forest night soldier"}
NO_RELEASE = "--no-release" in sys.argv


def sh(cmd, check=True):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, capture_output=False)


def release_exists(tag):
    if NO_RELEASE:
        return False
    return subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode == 0


def release_assets(tag):
    r = subprocess.run(["gh", "release", "view", tag, "--json", "assets"], capture_output=True, text=True)
    return [a["name"] for a in json.loads(r.stdout).get("assets", [])] if r.returncode == 0 else []


def try_upload(day):
    """Upload to YouTube once; mark the release with uploaded.txt so it never uploads twice."""
    r = subprocess.run([sys.executable, "upload_youtube.py", day])
    if r.returncode == 0:
        links = open("output/links.txt").read() if os.path.exists("output/links.txt") else ""
        open("output/uploaded.txt", "w").write(day + " uploaded\n" + links)
        if os.path.exists("output/links.txt"):
            os.remove("output/links.txt")
        subprocess.run(["gh", "release", "upload", day, "output/uploaded.txt", "--clobber"])
    elif r.returncode != 2:
        print(f"::warning::{day}: YouTube upload failed (video is still in the release)")


def thumb(lines, out, query=None):
    from make_video import make_bg  # reuse gradient
    import tempfile
    d = tempfile.mkdtemp()
    make_bg(1280, 720, os.path.join(d, "bg.png"))
    if query and (os.environ.get("PIXABAY_API_KEY") or os.environ.get("PEXELS_API_KEY")):
        try:
            import stock
            ph = stock.photo(query, os.path.join(d, "photo.jpg"))
            if ph:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ph, "-vf",
                                "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=brightness=-0.12:saturation=1.15,"
                                "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.35:t=fill", "-frames:v", "1", os.path.join(d, "bg.png")], check=True)
        except Exception as e:
            print("thumbnail photo failed, using plain background:", e)
    big, sub = (lines + [""])[:2]
    ass = "\n".join([
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1280", "PlayResY: 720", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Big,{FONT},150,&H003BD4FF,&H003BD4FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,6,0,5,60,60,0,1",
        f"Style: Sub,{FONT},64,&H00FFF4F0,&H00FFF4F0,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,60,60,60,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,0:00:00.00,0:00:05.00,Big,,0,0,0,,{big}",
        f"Dialogue: 0,0:00:00.00,0:00:05.00,Sub,,0,0,0,,{sub}",
    ])
    open(os.path.join(d, "t.ass"), "w", encoding="utf-8").write(ass)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", "bg.png", "-vf", "ass=t.ass" + (f":fontsdir={os.environ['FONTS_DIR']}" if os.environ.get("FONTS_DIR") else ""),
                    "-frames:v", "1", "-q:v", "2", os.path.abspath(out)], cwd=d, check=True)


def main():
    os.makedirs("output", exist_ok=True)
    built = []
    for meta_path in sorted(glob.glob("scripts/*.json")):
        meta = json.load(open(meta_path, encoding="utf-8"))
        day = meta["day"]
        if release_exists(day):
            if meta.get("channel") and "uploaded.txt" not in release_assets(day):
                print(f"{day}: built earlier but not uploaded yet, trying upload")
                os.makedirs("output", exist_ok=True)
                subprocess.run(["gh", "release", "download", day, "-D", "output", "--clobber"])
                try_upload(day)
            else:
                print(f"{day}: already done, skipping")
            continue
        dq = meta.get("stock_default") or DEFAULT_QUERY.get(meta.get("channel"), "city life")
        extra = ["--font", FONT, "--default-query", dq] + (["--test"] if TEST else []) + (["--brand", meta["brand"]] if meta.get("brand") else [])
        files = []
        if os.path.exists(f"scripts/{day}.txt"):
            sh([sys.executable, "make_video.py", f"scripts/{day}.txt"] + extra + (["--voice", meta["voice"]] if meta.get("voice") else []))
            files.append(f"output/{day}.mp4")
        if os.path.exists(f"scripts/{day}_short.txt"):
            sh([sys.executable, "make_video.py", f"scripts/{day}_short.txt", "--short"] + extra)
            files.append(f"output/{day}_short.mp4")
        if os.path.exists(f"scripts/{day}.txt"):
            thumb(meta.get("thumb", [meta.get("title", day)]), f"output/{day}_thumb.jpg",
                  meta.get("thumb_query") or meta.get("stock_default") or DEFAULT_QUERY.get(meta.get("channel")))
            files.append(f"output/{day}_thumb.jpg")
        chapters = ""
        if os.path.exists(f"output/{day}_chapters.txt"):
            chapters = open(f"output/{day}_chapters.txt", encoding="utf-8").read()
        desc = meta.get("description", "").replace("{chapters}", chapters)
        if os.environ.get("PIXABAY_API_KEY"):
            desc += "\n\nStock footage: Pixabay"
        elif os.environ.get("PEXELS_API_KEY"):
            desc += "\n\nStock footage: Pexels"
        open(f"output/{day}_description.txt", "w", encoding="utf-8").write(desc)
        files.append(f"output/{day}_description.txt")
        if not NO_RELEASE:
            sh(["gh", "release", "create", day, *files, "--title", meta.get("title") or meta.get("short_title", day),
                "--notes", f"Auto-built video for {day}"])
            try_upload(day)
        built.append(day)
    print("Built:", built or "nothing new")


if __name__ == "__main__":
    main()
