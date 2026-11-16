"""3D talking-cartoon Shorts (character B), one per matrix job.

scripts/mascot/<id>.txt   lines the character speaks (one subtitle line each, keep it 25-45 s)
scripts/mascot/<id>.json  {"channel": "money|english|tech", "title", "description", "publish": ISO time,
                           "tags": [...], "voice": "hi-IN-MadhurNeural", "brand": "Paisa Psychology"}
python mascot_job.py plan          -> prints JSON list of ids still to do (no uploaded.txt in release 3d-<id>)
python mascot_job.py run <id>      -> render (if not in release yet), publish release, upload to YouTube
"""
import glob, json, os, subprocess, sys

MASCOT_ID = "8635685"   # Pixabay 3D cartoon boy, black hair (character B, chosen 16 Nov 2026)
# The character is ALWAYS this same boy, and his voice must sound like a boy (Rahul, 16 Nov 2026):
# a young voice, not an adult man. Any "voice" key in the json is ignored on purpose.
VOICE, PITCH, RATE = "hi-IN-SwaraNeural", "+20Hz", "+6%"


def assets(tag):
    r = subprocess.run(["gh", "release", "view", tag, "--json", "assets"], capture_output=True, text=True)
    return None if r.returncode else [a["name"] for a in json.loads(r.stdout)["assets"]]


def plan():
    todo = []
    for p in sorted(glob.glob("scripts/mascot/*.json")):
        i = os.path.splitext(os.path.basename(p))[0]
        a = assets(f"3d-{i}")
        if a is None or "uploaded.txt" not in a:
            todo.append(i)
    print(json.dumps(todo[:12]))


def mascot_image(out="mascot.jpg"):
    import requests
    from PIL import Image
    h = requests.get("https://pixabay.com/api/", params={"key": os.environ["PIXABAY_API_KEY"], "id": MASCOT_ID},
                     timeout=30).json()["hits"][0]
    open("mascot.png", "wb").write(requests.get(h["largeImageURL"], timeout=60).content)
    Image.open("mascot.png").convert("RGB").save(out, quality=92)
    return out


def run(i):
    meta = json.load(open(f"scripts/mascot/{i}.json", encoding="utf-8"))
    tag, mp4 = f"3d-{i}", f"output/{i}.mp4"
    os.makedirs("output", exist_ok=True)
    have = assets(tag)
    if have and f"{i}.mp4" in have:
        subprocess.run(["gh", "release", "download", tag, "-p", f"{i}.mp4", "-D", "output", "--clobber"], check=True)
    else:
        subprocess.run([sys.executable, "avatar_video.py", "--photo", mascot_image(), "--script", f"scripts/mascot/{i}.txt",
                        "--out", mp4, "--voice", VOICE, "--pitch", PITCH, "--rate", RATE,
                        "--brand", meta.get("brand", "")], check=True)
        if have is None:
            subprocess.run(["gh", "release", "create", tag, mp4, "--title", meta["title"][:100], "--notes", "3D mascot Short"], check=True)
        else:
            subprocess.run(["gh", "release", "upload", tag, mp4, "--clobber"], check=True)
    import upload_youtube as yt
    ch = meta["channel"]
    if not (os.environ.get("YT_CLIENT_ID") and os.environ.get(yt.TOKEN_ENV[ch])):
        sys.exit(f"secrets for {ch} missing, will retry next run")
    title = meta["title"] if "#shorts" in meta["title"].lower() else meta["title"][:90] + " #shorts"
    vid = yt.upload(yt.access_token(ch), mp4, title, meta.get("description", ""), meta.get("tags", []),
                    yt.CATEGORY[ch], meta.get("publish"))
    open("output/uploaded.txt", "w").write(f"{i} https://youtu.be/{vid}\n")
    subprocess.run(["gh", "release", "upload", tag, "output/uploaded.txt", "--clobber"], check=True)


if __name__ == "__main__":
    plan() if sys.argv[1] == "plan" else run(sys.argv[2])
