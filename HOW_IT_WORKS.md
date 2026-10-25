# AI Hindi channel — daily automation

Each day N (day01 = 25 Oct 2026, day02 = 26 Oct, …):
1. Claude writes `scripts/dayNN.json` (+ `dayNN.txt` on long-video days, + `dayNN_short.txt`) from `plan.json` and pushes.
2. GitHub Actions (`build-videos.yml`) renders with the free edge-tts voice `hi-IN-SwaraNeural` and publishes release `dayNN`.
3. Claude schedules the release files to YouTube via Metricool (long 6 PM IST, Short 7 PM IST).

Script format: `# Section` lines start sections; every sentence becomes one caption screen. Write numbers as words.
`dayNN.json` keys: day, title, short_title, thumb [big, sub], description (with `{chapters}`), short_description, tags.
