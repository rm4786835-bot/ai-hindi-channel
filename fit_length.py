"""Keep long videos under YouTube's 15-minute limit for unverified channels.
If a video is longer than MAX seconds, speed it up slightly (audio pitch preserved) to fit."""
import os, subprocess, sys

_cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "max_video_seconds.txt")
MAX = float(os.environ.get("MAX_VIDEO_SECONDS") or (open(_cfg).read().strip() if os.path.exists(_cfg) else "885"))


def duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip())


def fit(path):
    d = duration(path)
    if d <= MAX:
        return d
    f = d / MAX
    print(f"{path}: {d:.0f}s > {MAX:.0f}s, speeding up x{f:.3f}")
    tmp = path + ".fit.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-filter_complex",
                    f"[0:v]setpts=PTS/{f:.5f}[v];[0:a]atempo={f:.5f}[a]", "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, path)
    return duration(path)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, fit(p))
