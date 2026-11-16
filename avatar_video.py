"""Talking-photo Short: Rahul's photo speaks the script (SadTalker, free, CPU), new background, Hindi subtitles.

python avatar_video.py --photo avatar/face1.jpg --script scripts/x_avatar.txt --out output/x.mp4
Script: plain lines; each line is one subtitle sentence. Lines starting with '#' are ignored.
"""
import argparse, asyncio, glob, os, re, subprocess, sys

SAD = os.environ.get("SADTALKER_DIR", "SadTalker")
FONT = os.environ.get("FONT", "Mukta")
FONTS_DIR = os.environ.get("FONTS_DIR", "")


def run(cmd, cwd=None):
    print("+", " ".join(cmd)[:200])
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode:
        sys.exit(f"failed: {cmd[0]}")


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip())


def ts(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


async def tts(text, out, voice, rate, pitch="+0Hz"):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice", default="hi-IN-MadhurNeural")
    ap.add_argument("--rate", default="+8%")
    ap.add_argument("--pitch", default="+0Hz", help="e.g. +25Hz makes a child-like voice")
    ap.add_argument("--brand", default="")
    a = ap.parse_args()
    work = os.path.abspath("build/avatar_" + os.path.splitext(os.path.basename(a.out))[0]); os.makedirs(work, exist_ok=True)
    lines = [l.strip() for l in open(a.script, encoding="utf-8") if l.strip() and not l.startswith("#")]

    # 1. voice, one sentence at a time (gives subtitle timing)
    parts, times, t = [], [], 0.0
    for i, s in enumerate(lines):
        p = os.path.join(work, f"v{i:02d}.mp3")
        for k in range(4):
            try:
                asyncio.run(tts(s, p, a.voice, a.rate, a.pitch)); break
            except Exception as e:
                if k == 3:
                    raise
                print("tts retry", e)
        d = dur(p) + 0.15
        times.append((t, t + d)); t += d; parts.append(p)
    open(os.path.join(work, "list.txt"), "w").write("\n".join(f"file '{p}'" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt",
         "-af", "apad=pad_dur=0.15", "-ar", "16000", "-ac", "1", "voice.wav"], cwd=work)
    try:  # log the voice pitch so a wrong (adult/child) voice is easy to spot
        import librosa, numpy as np
        y, sr = librosa.load(os.path.join(work, "voice.wav"), sr=16000)
        f0 = librosa.yin(y, fmin=70, fmax=500, sr=sr)
        print(f"::notice::voice {a.voice} {a.pitch}: median pitch {np.median(f0):.0f} Hz")
    except Exception as e:
        print("pitch check skipped", e)

    # 2. the photo talks
    res = os.path.join(work, "sad")
    run([sys.executable, "inference.py", "--driven_audio", os.path.join(work, "voice.wav"),
         "--source_image", os.path.abspath(a.photo), "--result_dir", res, "--preprocess", "full", "--still",
         "--size", "256", "--expression_scale", "1.1", "--cpu"], cwd=SAD)
    talk = sorted(glob.glob(os.path.join(res, "**", "*.mp4"), recursive=True), key=os.path.getmtime)[-1]

    # 3. subtitles (bottom third, so the face stays clear)
    ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 0", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
           "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Main,{FONT},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,6,2,2,70,70,360,1",
           f"Style: Mark,{FONT},40,&H00E6D2C8,&H00E6D2C8,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,9,40,60,70,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    if a.brand:
        ass.append(f"Dialogue: 0,{ts(0)},{ts(t)},Mark,,0,0,0,,{a.brand}")
    for s, (x, y) in zip(lines, times):
        s = re.sub(r"([A-Za-z][A-Za-z']+)", r"{\\c&H3BD4FF&}\1{\\c&HFFFFFF&}", s)
        ass.append(f"Dialogue: 0,{ts(x)},{ts(y)},Main,,0,0,0,,{{\\fad(100,60)}}{s}")
    open(os.path.join(work, "subs.ass"), "w", encoding="utf-8").write("\n".join(ass) + "\n")

    # 4. 9:16 frame: blurred photo fills the back, the talking video sits on top, gentle push-in
    fd = f":fontsdir={FONTS_DIR}" if FONTS_DIR else ""
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", talk, "-i", os.path.join(work, "voice.wav"), "-filter_complex",
         "[0:v]split[a][b];"
         "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-0.08[bg];"
         "[b]scale=1080:-2,eq=contrast=1.06:saturation=1.08,"
         "zoompan=z='min(1.0+0.0006*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':d=1:s=1080x1440:fps=25[fg];"
         f"[bg][fg]overlay=0:120,ass={os.path.join(work, 'subs.ass')}{fd}[v]",
         "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", os.path.abspath(a.out)])
    print("done", a.out, f"{t:.1f}s")


if __name__ == "__main__":
    main()
