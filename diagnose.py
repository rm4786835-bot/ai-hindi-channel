"""Check every uploaded video: is it really public, and how many views."""
import json, re, subprocess, requests
rels = json.loads(subprocess.run(["gh", "release", "list", "--limit", "100", "--json", "tagName"], capture_output=True, text=True).stdout)
rows = []
for r in rels:
    tag = r["tagName"]
    out = subprocess.run(["gh", "release", "download", tag, "-p", "uploaded.txt", "-O", "-"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        m = re.search(r"(\S+\.mp4) https://youtu.be/(\S+)", line)
        if not m:
            continue
        vid = m.group(2)
        o = requests.get("https://www.youtube.com/oembed", params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"}, timeout=30)
        h = requests.get(f"https://www.youtube.com/watch?v={vid}", headers={"Accept-Language": "en-US", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}, timeout=30).text
        if '"viewCount"' not in h:
            h = requests.get(f"https://www.youtube.com/shorts/{vid}", headers={"Accept-Language": "en-US", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}, timeout=30).text
        views = re.search(r'"viewCount":"(\d+)"', h)
        status = re.search(r'"playabilityStatus":\{"status":"(\w+)"(?:,"reason":"([^"]*)")?', h)
        unlisted = '"isUnlisted":true' in h
        rows.append(f"{tag} {m.group(1)} {vid} oembed={o.status_code} play={status.group(1) if status else '?'} reason={status.group(2) if status and status.group(2) else '-'} unlisted={unlisted} views={views.group(1) if views else '?'}")
short = [f"{x.split()[1]}:{x.split('oembed=')[1].split()[0]}:{x.split('views=')[1]}" for x in rows]
print("::notice::" + " | ".join(short))
