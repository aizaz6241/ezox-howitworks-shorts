# EZOXIFY daily "How it works" Short — runbook

One run = one new vertical YouTube Short (1080x1920, **30–60 s**), Urdu voice-over, Urdu captions,
cinematic animation, uploaded **public** to the EZOXIFY channel. The owner (Aizaz) has said: no approval,
fully automatic, every day. Do not stop to ask anything; take the most reasonable choice and continue.

## 0. Setup (each run starts from a fresh machine)
```bash
W=/home/claude/run; mkdir -p $W && cd $W
git clone https://github.com/aizaz6241/ezox-howitworks-shorts.git repo          # this repo (needs push access: add_repo owner=aizaz6241 repo=ezox-howitworks-shorts access=push)
git clone https://github.com/Moh4696/cinematic-skill.git skill && git -C skill checkout bf435561c6203f90f971300efe952b68b5ec3417
S=$W/skill/skills/cinematic-film/scripts
pip install --break-system-packages -q skia-python scipy numpy pillow
mkdir -p fonts && curl -sL -o fonts/NotoNastaliqUrdu.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/notonastaliqurdu/NotoNastaliqUrdu%5Bwght%5D.ttf"
python3 -c "from PIL import features; assert features.check('raqm')"
python3 $S/check_setup.py
```
Read `skill/skills/cinematic-film/SKILL.md` and its `references/film.md` once. The skill's "approval gates"
are skipped (owner's standing instruction). Its `burn_captions.py` cannot shape Urdu: use `repo/tools/urdu_captions.py`.

## 1. Don't double-post
Read `repo/log.json`. If an entry already has today's date (Asia/Karachi) with a `video_id`, stop: nothing to do.

## 2. Pick today's topic
- "How it works" for an everyday thing ordinary Pakistani people use or see but don't understand
  (phone/tech, home appliances, the body, vehicles & roads, money & banking, internet, food & kitchen, weather & nature, buildings, medicine basics).
- Never repeat a topic in `log.json`, and don't pick a near-duplicate. Rotate categories (not the same category as the last 3).
- Check the key facts with 2–3 web searches before writing. Keep every claim simple and true; no medical/financial advice, no politics, no religion, no fear-bait.

## 3. Script (Urdu script, not Roman)
- 8–12 lines. Line 1 = a curiosity hook question. Last line = short follow CTA (vary the wording).
- Spoken length target 32–55 s. Simple everyday words, one idea per line, an analogy where it helps.
- Each line has `"id"`, `"text"` (= caption), `"spoken"` (same Urdu), `"hero"` (what's on screen), `"typed"` (short ENGLISH CAPS label or "").
- Write `proj/script.json` in the same shape as `examples/touchscreen_script.json` (takes → lines), plus `"title"` and `"fact_notes"`.

## 4. Voice
```bash
P=$W/proj; mkdir -p $P && cd $W && python3 $S/new_project.py proj   # if it refuses an existing dir, run it before writing script.json
ELEVEN_API_KEY=<key from the task prompt> python3 repo/tools/tts_eleven.py --project $P
python3 $S/build_narration.py --project $P --lead 0.3 --tail 1.1
```
`total_duration` in `audio/timing.json` must be 30–60 s. Outside that: shorten/lengthen the script and redo this step.
The tool uses Saira (Urdu storyteller) and falls back to a premade voice if the plan refuses it — note that in the log.

## 5. Scene
- Write `$P/scene.py` fresh for this topic (a new visual world each day — not the touchscreen layout).
  Study `examples/touchscreen_scene.py` for the vertical-format rules and the Urdu-aware `W(i, word)` helper that reads `audio/word_times.json`.
- Vertical rules: render `--size 1080x1920`; zoom 1 shows 3840 x 6827 world px; keep heroes in the top ~60 %
  (camera y = hero_y + 819/zoom); keep the band 62–78 % of frame height free for captions; on-screen type ≥ 3 % of frame height.
- Cinematic: one continuous camera, effects land on the spoken word (`W`), sound cues on hits (`film.cue`), glow/night or another look that fits.
- `python3 $S/prep_assets.py --project $P`, then probe 6–10 stills: `python3 $S/render.py --project $P --probe t1,t2,... --size 1080x1920`.
  LOOK at them (contact sheet). Fix clipping, overlaps, empty frames, unreadable text before the full render.

## 6. Render
```bash
python3 $S/render.py --project $P --cues && python3 $S/build_sfx.py --project $P && python3 $S/mix_soundtrack.py --project $P
python3 $S/render.py --project $P --size 1080x1920 --workers 3 --out $P/out/nocap.mp4 --audio $P/audio/mix.m4a
python3 repo/tools/urdu_captions.py --project $P --font fonts/NotoNastaliqUrdu.ttf --video $P/out/nocap.mp4 --out $P/out/short.mp4
```
Check: duration 30–60 s, 1080x1920, has audio, 3 frames look right. If > 90 MB, re-encode with `-crf 24`.

## 7. Publish the file (public URL for Zapier)
```bash
cd $W && rm -rf media && mkdir media && cd media && git init -q -b media && cp $P/out/short.mp4 short.mp4
git add short.mp4 && git commit -qm "media $(date +%F)" && git remote add origin https://github.com/aizaz6241/ezox-howitworks-shorts.git && git push -qf origin media
URL=https://raw.githubusercontent.com/aizaz6241/ezox-howitworks-shorts/media/short.mp4
curl -sI $URL | head -1    # must be 200 (wait/retry up to 2 min for the CDN)
```
(The `media` branch only ever holds today's video — it is force-pushed.)

## 8. Upload to YouTube (Zapier MCP)
Load the Zapier tools first if they are deferred (ToolSearch query `zapier`). Upload must be public, no approval needed.
`execute_zapier_write_action` — app YouTube (`YouTubeV4CLIAPI`), action `upload_video`, connection is the default (EZOXIFY):
- `video`: the raw URL above
- `title`: ≤ 90 chars, Urdu hook + 1–2 English words + `#shorts` (e.g. `دستانے سے فون کیوں نہیں چلتا؟ 🤯 Touch Screen #shorts`)
- `description`: 2–3 Urdu lines of what the viewer learns, one English line, then `#howitworks #urdu #shorts #science`
- `privacy_status`: `public`, `made_for_kids`: `false`, `notify_subscribers`: `true`, `default_language`: `ur`,
  `default_audio_language`: `ur`, `tags`: 6–10 Urdu/English keywords, `category_id`: Education (resolve the enum via inspect_zapier_actions once).
Record the returned video id.

## 9. Log
Append to `repo/log.json`: `{"date","topic","category","title","video_id","duration","voice"}`; commit and push to `main`.

## Failure rules
- Retry a failed step once. Never upload a video that failed a check in step 6.
- If ElevenLabs is out of credits or the key is rejected, or YouTube upload fails twice: log the failure with the reason, keep the rendered file, and end the run with a short message saying exactly what the owner must fix.
- Never write the API key into the repo, the log, a commit or any file.
