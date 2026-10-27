# Three YouTube channels — daily automation (all free)

| Channel | id prefix | day 01 = | json "channel" | brand (watermark) | Long publish | Short publish |
|---|---|---|---|---|---|---|
| Tech + AI (rm4786835) | dayNN | 2026-10-25 | tech | AI Hindi | 18:00 IST | 19:00 IST |
| English (mouryarahul37, "the end of life") | engNN | 2026-10-26 | english | Roz Ki English | 08:00 IST | 13:00 IST |
| Money + Mind (rm0199482) | moneyNN | 2026-10-26 | money | Paisa Psychology | 20:00 IST | 21:00 IST |
| Action stories (new 4th channel) | actNN (NN = 01, 02, … per episode) | first episode once YT_TOKEN_ACTION exists | action | Action Kahani | 21:30 IST (Mon/Wed/Fri) | 22:30 IST |

Plans: plan.json (tech, long only on days that have "long"), plan_english.json (long + short every day), plan_money.json (long + short every day).

Flow per id: write scripts/<id>.txt (long), scripts/<id>_short.txt, scripts/<id>.json → push → GitHub Actions "Build videos" renders (free edge-tts voices),
creates release <id>, uploads to YouTube with the official API (upload_youtube.py), and marks the release with uploaded.txt.
If a channel's secret is missing the upload retries on the next run. Times in json: publish_long / publish_short (ISO with +05:30);
if the time is in the future the video is uploaded private and YouTube makes it public at that time.

Script format: "# Section" lines; every sentence = one caption screen; numbers as words; no emoji in .txt.
English channel: a line starting with "EN:" is spoken by the Indian-English voice and shown in yellow; explain in Hindi, model sentences in EN lines.
json keys: day, channel, brand, publish_long, publish_short, title, short_title, thumb [big, sub], description (with "Chapters:\n{chapters}" if long), short_description, tags.

## Real footage (free, Pixabay or Pexels)
If the PIXABAY_API_KEY (preferred) or PEXELS_API_KEY secret exists, every video uses real HD stock footage instead of the plain background, plus soft generated music.
In scripts put a line `@ english search words` before sentences to choose the footage (e.g. `@ indian student studying laptop`,
`@ office team meeting`, `@ rupee notes counting`). Use concrete, visual English words (2–5 words), change it every 1–3 sentences
so scenes follow the narration. Optional json keys: "stock_default" (fallback search), "thumb_query" (photo behind the thumbnail text).

## Story films (Money channel, EVERY DAY)
Every day the money long video is a "कहानी फिल्म": a 12–16 minute original fictional Indian story (about 2000–2600 spoken words)
that teaches that day's plan_money.json topic through the characters' lives. json gets "voice": "hi-IN-MadhurNeural" (male storyteller)
and "story": true; the Short is a teaser of the story's most gripping moment. Footage lines follow each scene's mood and setting
(village, rain, hospital, office, family dinner). Description says "यह कहानी काल्पनिक है" and lists the money lesson.

## Action story films (4th channel, Mon/Wed/Fri)
Original survival / battle-royale-style action thrillers (island, 100 strangers, only one survives; betrayal, alliances, twist after twist).
15–20 minutes (2500–3200 words), male storyteller voice hi-IN-MadhurNeural, json "channel": "action", "brand": "Action Kahani", "voice", "story": true.
NEVER use the names, logos, maps, weapons names, characters or footage of BGMI/PUBG/Free Fire or any real game, film or brand — fully original
world and characters. No gore or glorified real-world violence; keep it cinematic and suitable for a general audience (no graphic injury detail).
Footage "@" lines: forest night, soldiers silhouette, helicopter, explosion distant, rain storm, abandoned building, running feet, sunrise.
Description: "यह कहानी काल्पनिक है". Episodes may continue a story arc ("भाग 1, भाग 2") to bring viewers back.
