"""Re-upload the LONG video of given ids (e.g. after 'Video too long'). Usage: python reupload.py money02 money03"""
import datetime as dt, json, os, subprocess, sys
args = sys.argv[1:]
if "full" in args:  # channel is phone-verified: keep the original length
    os.environ["MAX_VIDEO_SECONDS"] = "3600"
    args = [a for a in args if a != "full"]
import importlib, fit_length, upload_youtube as U
importlib.reload(fit_length)

for day in args:
    meta = json.load(open(f"scripts/{day}.json", encoding="utf-8"))
    os.makedirs("output", exist_ok=True)
    subprocess.run(["gh", "release", "download", day, "-D", "output", "--clobber", "-p", f"{day}.mp4",
                    "-p", f"{day}_description.txt", "-p", f"{day}_thumb.jpg", "-p", "uploaded.txt"], check=True)
    fit_length.fit(f"output/{day}.mp4")
    tok = U.access_token(meta["channel"])
    pub = meta.get("publish_long")
    if pub and dt.datetime.fromisoformat(pub) < dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10):
        pub = None
    desc = open(f"output/{day}_description.txt", encoding="utf-8").read()
    vid = U.upload(tok, f"output/{day}.mp4", meta["title"], desc, meta.get("tags", []), U.CATEGORY[meta["channel"]], pub)
    if os.path.exists(f"output/{day}_thumb.jpg"):
        U.set_thumb(tok, vid, f"output/{day}_thumb.jpg")
    old = open("output/uploaded.txt", encoding="utf-8").read() if os.path.exists("output/uploaded.txt") else ""
    links = open("output/links.txt", encoding="utf-8").read() if os.path.exists("output/links.txt") else ""
    open("output/uploaded.txt", "w", encoding="utf-8").write(old + "re-upload:\n" + links)
    if os.path.exists("output/links.txt"):
        os.remove("output/links.txt")
    subprocess.run(["gh", "release", "upload", day, "output/uploaded.txt", "--clobber"], check=True)
    os.remove(f"output/{day}.mp4")
