# Three YouTube channels — daily automation (all free)

| Channel | id prefix | day 01 = | json "channel" | brand (watermark) | Long publish | Short publish |
|---|---|---|---|---|---|---|
| Tech + AI (rm4786835) | dayNN | 2026-10-25 | tech | AI Hindi | 18:00 IST | 19:00 IST |
| English (mouryarahul37, "the end of life") | engNN | 2026-10-26 | english | Roz Ki English | 08:00 IST | 13:00 IST |
| Money + Mind (rm0199482) | moneyNN | 2026-10-26 | money | Paisa Psychology | 20:00 IST | 21:00 IST |

Plans: plan.json (tech, long only on days that have "long"), plan_english.json (long + short every day), plan_money.json (long + short every day).

Flow per id: write scripts/<id>.txt (long), scripts/<id>_short.txt, scripts/<id>.json → push → GitHub Actions "Build videos" renders (free edge-tts voices),
creates release <id>, uploads to YouTube with the official API (upload_youtube.py), and marks the release with uploaded.txt.
If a channel's secret is missing the upload retries on the next run. Times in json: publish_long / publish_short (ISO with +05:30);
if the time is in the future the video is uploaded private and YouTube makes it public at that time.

Script format: "# Section" lines; every sentence = one caption screen; numbers as words; no emoji in .txt.
English channel: a line starting with "EN:" is spoken by the Indian-English voice and shown in yellow; explain in Hindi, model sentences in EN lines.
json keys: day, channel, brand, publish_long, publish_short, title, short_title, thumb [big, sub], description (with "Chapters:\n{chapters}" if long), short_description, tags.
