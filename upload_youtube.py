"""Upload a built day to YouTube with the official API (free).

Needs env: YT_CLIENT_ID, YT_CLIENT_SECRET and the channel's refresh token
(YT_TOKEN_TECH / YT_TOKEN_ENGLISH / YT_TOKEN_MONEY).

Usage: python upload_youtube.py dayNN            (reads scripts/dayNN.json and output/dayNN*)
       python upload_youtube.py --check          (only checks every token works)
The day's json must contain "channel": "tech" | "english" | "money"; otherwise nothing is uploaded.
Optional json keys: "publish_long" / "publish_short" as ISO time (e.g. 2026-10-27T18:00:00+05:30).
If a publish time is in the future the video is uploaded private and YouTube makes it public then.
"""
import datetime as dt, json, os, sys, time
import requests

TOKEN_ENV = {"tech": "YT_TOKEN_TECH", "english": "YT_TOKEN_ENGLISH", "money": "YT_TOKEN_MONEY"}
CATEGORY = {"tech": "28", "english": "27", "money": "27"}  # 28 Science & Tech, 27 Education
DONE_DIR = "uploaded"


def access_token(channel):
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ[TOKEN_ENV[channel]], "grant_type": "refresh_token"}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"[{channel}] token refresh failed: {r.status_code} {r.text[:300]}")
    return r.json()["access_token"]


def upload(tok, path, title, desc, tags, category, publish_at):
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False}
    if publish_at and dt.datetime.fromisoformat(publish_at) > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10):
        status["privacyStatus"] = "private"
        status["publishAt"] = dt.datetime.fromisoformat(publish_at).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {"snippet": {"title": title[:100], "description": desc[:4900], "tags": tags,
                        "categoryId": category, "defaultLanguage": "hi", "defaultAudioLanguage": "hi"},
            "status": status}
    size = os.path.getsize(path)
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
         "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers=h, data=json.dumps(meta), timeout=60)
    if r.status_code not in (200, 201):
        sys.exit(f"start upload failed: {r.status_code} {r.text[:500]}")
    url = r.headers["Location"]
    for attempt in range(5):
        with open(path, "rb") as f:
            r = requests.put(url, headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"}, data=f, timeout=1800)
        if r.status_code in (200, 201):
            v = r.json()
            print(f"Uploaded {path}: https://youtu.be/{v['id']}  status={v['status'].get('privacyStatus')} "
                  f"publishAt={v['status'].get('publishAt')} uploadStatus={v['status'].get('uploadStatus')}")
            return v["id"]
        print(f"retry {attempt+1}: {r.status_code} {r.text[:200]}"); time.sleep(10 * (attempt + 1))
    sys.exit("upload failed after retries")


def set_thumb(tok, vid, path):
    with open(path, "rb") as f:
        r = requests.post(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}",
                          headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/jpeg"}, data=f, timeout=120)
    print("thumbnail:", r.status_code, "" if r.ok else r.text[:300])


def main():
    if "--check" in sys.argv:
        for ch, env in TOKEN_ENV.items():
            if os.environ.get(env):
                tok = access_token(ch)
                r = requests.get("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                                 headers={"Authorization": f"Bearer {tok}"}, timeout=60)
                items = r.json().get("items", []) if r.ok else []
                print(f"[{ch}] OK -> channel: {items[0]['snippet']['title'] if items else '(read not permitted with upload-only scope, token works)'}")
            else:
                print(f"[{ch}] secret {env} not set")
        return
    day = sys.argv[1]
    meta = json.load(open(f"scripts/{day}.json", encoding="utf-8"))
    ch = meta.get("channel")
    if not ch:
        print(f"{day}: no 'channel' in json, skipping YouTube API upload"); return
    if not (os.environ.get("YT_CLIENT_ID") and os.environ.get(TOKEN_ENV[ch])):
        print(f"{day}: secrets for '{ch}' not set, skipping"); return
    os.makedirs(DONE_DIR, exist_ok=True)
    tok = access_token(ch)
    cat = CATEGORY[ch]
    if os.path.exists(f"output/{day}.mp4"):
        desc = open(f"output/{day}_description.txt", encoding="utf-8").read()
        vid = upload(tok, f"output/{day}.mp4", meta["title"], desc, meta.get("tags", []), cat, meta.get("publish_long"))
        if os.path.exists(f"output/{day}_thumb.jpg"):
            set_thumb(tok, vid, f"output/{day}_thumb.jpg")
    if os.path.exists(f"output/{day}_short.mp4"):
        title = meta.get("short_title") or meta["title"]
        if "#shorts" not in title.lower():
            title = (title[:90] + " #shorts")
        upload(tok, f"output/{day}_short.mp4", title, meta.get("short_description", ""), meta.get("tags", []), cat,
               meta.get("publish_short"))


if __name__ == "__main__":
    main()
