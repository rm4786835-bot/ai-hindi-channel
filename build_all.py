"""Builds every day in scripts/ that has no GitHub release yet.
For dayNN it makes: dayNN.mp4 (long), dayNN_short.mp4 (if script exists), dayNN_thumb.jpg,
dayNN_description.txt (chapters filled in), and publishes them as release "dayNN"."""
import glob, json, os, subprocess, sys

FONT = os.environ.get("FONT", "Noto Sans Devanagari")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
TEST = "--test" in sys.argv
NO_RELEASE = "--no-release" in sys.argv


def sh(cmd, check=True):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, capture_output=False)


def release_exists(tag):
    if NO_RELEASE:
        return False
    return subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode == 0


def thumb(lines, out):
    from make_video import make_bg  # reuse gradient
    import tempfile
    d = tempfile.mkdtemp()
    make_bg(1280, 720, os.path.join(d, "bg.png"))
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
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", "bg.png", "-vf", "ass=t.ass",
                    "-frames:v", "1", "-q:v", "2", os.path.abspath(out)], cwd=d, check=True)


def main():
    os.makedirs("output", exist_ok=True)
    built = []
    for meta_path in sorted(glob.glob("scripts/*.json")):
        meta = json.load(open(meta_path, encoding="utf-8"))
        day = meta["day"]
        if release_exists(day):
            print(f"{day}: already published, skipping")
            continue
        extra = ["--font", FONT] + (["--test"] if TEST else [])
        files = []
        if os.path.exists(f"scripts/{day}.txt"):
            sh([sys.executable, "make_video.py", f"scripts/{day}.txt"] + extra)
            files.append(f"output/{day}.mp4")
        if os.path.exists(f"scripts/{day}_short.txt"):
            sh([sys.executable, "make_video.py", f"scripts/{day}_short.txt", "--short"] + extra)
            files.append(f"output/{day}_short.mp4")
        if os.path.exists(f"scripts/{day}.txt"):
            thumb(meta.get("thumb", [meta.get("title", day)]), f"output/{day}_thumb.jpg")
            files.append(f"output/{day}_thumb.jpg")
        chapters = ""
        if os.path.exists(f"output/{day}_chapters.txt"):
            chapters = open(f"output/{day}_chapters.txt", encoding="utf-8").read()
        desc = meta.get("description", "").replace("{chapters}", chapters)
        open(f"output/{day}_description.txt", "w", encoding="utf-8").write(desc)
        files.append(f"output/{day}_description.txt")
        if not NO_RELEASE:
            sh(["gh", "release", "create", day, *files, "--title", meta.get("title") or meta.get("short_title", day),
                "--notes", f"Auto-built video for {day}"])
            r = subprocess.run([sys.executable, "upload_youtube.py", day])
            if r.returncode != 0:
                print(f"::warning::{day}: YouTube upload failed (video is still in the release)")
        built.append(day)
    print("Built:", built or "nothing new")


if __name__ == "__main__":
    main()
