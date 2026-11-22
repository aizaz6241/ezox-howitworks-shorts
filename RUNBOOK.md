# EZOXIFY daily "How it works" Short — runbook

One run = one new vertical YouTube **Short** (1080x1920, **30–60 s**), Urdu voice-over, Urdu captions,
beautiful cinematic animation, a designed thumbnail, uploaded **public** to the EZOXIFY channel.
The owner (Aizaz) has said: no approval, fully automatic, every day. Never stop to ask; take the most
reasonable choice and continue. Quality bar: a viewer swiping the Shorts feed must stop in the first second,
understand everything, and think "wah". Spend effort on the topic, the hook and the visuals.

Spend credits carefully (ElevenLabs characters, Zapier tasks): one voice generation per day at most, no
experiments against the paid APIs, reuse anything already made (see "Resume").

## 0. Setup (each run starts from a fresh machine)
```bash
W=/home/claude/run; mkdir -p $W && cd $W
git clone https://github.com/aizaz6241/ezox-howitworks-shorts.git repo   # attach first: add_repo owner=aizaz6241 repo=ezox-howitworks-shorts access=push
git -C repo fetch -q origin media:media 2>/dev/null || true
cp -r repo/vendor/cinematic-skill skill     # MIT-licensed copy of github.com/Moh4696/cinematic-skill @ bf435561 (kept here so the pipeline never breaks)
S=$W/skill/skills/cinematic-film/scripts
pip install --break-system-packages -q skia-python scipy numpy pillow
mkdir -p fonts
curl -sL -o fonts/NotoNastaliqUrdu.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/notonastaliqurdu/NotoNastaliqUrdu%5Bwght%5D.ttf"
curl -sL -o fonts/Anton.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
python3 -c "from PIL import features; assert features.check('raqm')"
python3 $S/check_setup.py
```
Read `skill/skills/cinematic-film/SKILL.md` and `references/film.md`. Skip the skill's approval gates (owner's
standing instruction). Use other skills too if they make the result better. The skill's `burn_captions.py`
cannot shape Urdu: use `repo/tools/urdu_captions.py`.

## 1. Resume before making anything new
`git -C repo show media:pending.json` (if it exists) describes work from an earlier run that did not finish:
- `"stage": "rendered"` → the video `media:short.mp4` + `media:thumb.jpg` are ready: go straight to step 9
  (upload) with the title/description/tags stored in pending.json. Do NOT make a new video today.
- `"stage": "uploaded"` (thumbnail missing) → only do step 10 for its `video_id`, then continue normally.
- `"stage": "voiced"` → `media:pending/` holds script.json + audio/: reuse them (skip steps 3–5 voice generation).

## 2. Don't double-post
If `repo/log.json` already has today's date (Asia/Karachi) with a `video_id`, stop: nothing to do.

## 3. Topic — something people are *dying* to know
- Use `repo/topics_bank.md` (or invent a better one in that spirit). Never repeat or near-repeat a topic in
  `log.json`; don't use the same category as the last 2 entries.
- The test: would a normal person in Pakistan, seeing the question, *need* the answer? Everyday object or
  experience + surprising mechanism. No politics, religion, medical/financial advice, fear-bait or gore.
- Verify the key facts with 2–3 web searches. Every claim simple and true.

## 4. Script (Urdu script for voice and captions)
- 9–13 lines, spoken 35–55 s, at most 1100 characters in total.
- **Line 1 = the hook**, ≤ 2.5 s, a question that itches ("…kyun?" / "kabhi socha hai…?"). Line 2 opens a loop
  ("jawab aap ki soch se bilkul alag hai"). Then the explanation in simple everyday words with one analogy,
  each line one idea. One "wow" fact near the end. Last line = short follow CTA (vary the wording).
- Each line: `"id"`, `"text"` (caption), `"spoken"` (same Urdu), `"hero"` (what's on screen), `"typed"`
  (short ENGLISH CAPS label or ""). Also top-level `"title"`, `"hook_roman"` (the hook in Roman Urdu CAPS,
  3–7 words, e.g. `DASTANE SE PHONE KYUN NAHI CHALTA?`) and `"fact_notes"`. Shape: `examples/touchscreen_script.json`.

## 5. Voice (guarded)
```bash
cd $W && python3 $S/new_project.py proj; P=$W/proj      # then write $P/script.json
ELEVEN_API_KEY=<key> python3 repo/tools/credits.py --project $P   # exit 3 = not enough credits, 4 = key/plan problem, 5 = shorten script
ELEVEN_API_KEY=<key> python3 repo/tools/tts_eleven.py --project $P
python3 $S/build_narration.py --project $P --lead 0.25 --tail 1.0
```
- credits.py exit 3 or 4: do NOT generate anything. Log `{"date","status":"skipped","reason"}` and end the run
  with a message telling Aizaz what to fix (top up / renew ElevenLabs). Exit 5: shorten the script, retry.
- `audio/timing.json` `total_duration` must be 30–60 s. If it's off by a little, adjust gaps in segments.json and
  rerun build_narration (free). Only if it's way off, edit the script and regenerate just the changed lines.
- Right after the voice is made, save it so a failure later never costs credits again:
  push `script.json` + `audio/` to `media:pending/` with `pending.json` `{"stage":"voiced",...}` (see step 8 for how to push).

## 6. Scene — make it beautiful
- Write `$P/scene.py` fresh for this topic: a new visual world, palette and look each day (not the touchscreen layout).
  Study `examples/touchscreen_scene.py` for the vertical rules and the Urdu-aware `W(i, word)` helper (reads `audio/word_times.json`).
- **First frame is the hook**: at t = 0 the screen already shows the most intriguing visual plus the big Roman Urdu
  hook text (`hook_roman`, Bebas/cond, ≥ 7 % of frame height, one word highlighted) — no fade from black
  (`film.fade_in = 0`), movement within 0.3 s. This first frame also works as a fallback thumbnail.
- Every line gets a new visual beat landing on its key word (`W`), with a sound cue on hits. Kinetic labels,
  glow, particles, depth, a moving camera; no empty or static stretch longer than ~1.5 s. End card with FOLLOW.
- Vertical rules: `--size 1080x1920`; zoom 1 shows 3840 x 6827 world px; heroes in the top ~60 %
  (camera y = hero_y + 819/zoom); keep 62–78 % of frame height free for captions; type ≥ 3 % of frame height.
- `python3 $S/prep_assets.py --project $P`, then probe 8–12 stills (`render.py --probe ... --size 1080x1920`),
  make a contact sheet and LOOK at it. Fix clipping, overlaps, dull or empty frames before the full render.

## 7. Render + captions + checks
```bash
python3 $S/render.py --project $P --cues && python3 $S/build_sfx.py --project $P && python3 $S/mix_soundtrack.py --project $P
python3 $S/render.py --project $P --size 1080x1920 --workers 3 --out $P/out/nocap.mp4 --audio $P/audio/mix.m4a
python3 repo/tools/urdu_captions.py --project $P --font fonts/NotoNastaliqUrdu.ttf --video $P/out/nocap.mp4 --out $P/out/short.mp4
```
Check: 30–60 s, 1080x1920 (vertical → YouTube files it as a Short), audio present, 4 frames look right.
Re-encode with `-crf 24` if > 90 MB.

Thumbnail (1080x1920 JPG): grab the most intriguing moment from `nocap.mp4` (no captions), then
```bash
python3 repo/tools/thumbnail.py --frame still.png --font fonts/Anton.ttf --out $P/out/thumb.jpg \
  --line "..." --line "..." --hi "<one word>" --point X,Y
```
3–7 words of Roman Urdu CAPS over 2–3 lines, one highlighted word, ring+arrow on the thing (`--point` in
1080x1920 still coordinates). LOOK at it; it must be bold, clean, readable at phone-grid size.

## 8. Publish the files (public URLs for Zapier)
```bash
cd $W && rm -rf media && git clone -q -b media https://github.com/aizaz6241/ezox-howitworks-shorts.git media 2>/dev/null || (mkdir media && git -C media init -q -b media)
cd media && git rm -rqf . 2>/dev/null; cp $P/out/short.mp4 $P/out/thumb.jpg . && cat > pending.json   # {"stage":"rendered","date":...,"title":...,"description":...,"title_en":...,"description_en":...,"tags":[...],"topic":...,"category":...,"duration":...}
git add -A && git -c user.name=aizaz6241 -c user.email=aizaz6241@users.noreply.github.com commit -qm "media $(date +%F)"
git remote get-url origin >/dev/null 2>&1 || git remote add origin https://github.com/aizaz6241/ezox-howitworks-shorts.git
git push -qf origin media
for f in short.mp4 thumb.jpg; do curl -sI https://raw.githubusercontent.com/aizaz6241/ezox-howitworks-shorts/media/$f | head -1; done   # both 200 (retry up to 2 min)
```
(`media` only ever holds the current day's files; it is force-pushed. The same steps push `pending/` in step 5.)

## 9. Upload to YouTube (Zapier MCP — load the tools with ToolSearch `zapier` if they are deferred)
One `execute_zapier_write_action` call: app YouTube (`YouTubeV4CLIAPI`), action `upload_video`
(tool_name `youtube_upload_video`), default connection = EZOXIFY. No inspect calls needed — these params are known:
- `video`: `https://raw.githubusercontent.com/aizaz6241/ezox-howitworks-shorts/media/short.mp4`
- `title`: Roman Urdu, ≤ 70 chars, curiosity + 1 emoji + `#shorts` (e.g. `Dastane Se Phone Kyun Nahi Chalta? 🤯 #shorts`)
- `description`: 2–3 Roman Urdu lines (what you'll learn) / blank line / 1–2 English lines / blank line /
  one Urdu-script line / blank line / `#howitworks #urdu #shorts #science #<topic> #EZOXIFY`
- `language_code`: `en`, `localized_title`: the English title (≤ 70 chars + emoji + #shorts), `localized_description`: English description
- `privacy_status` `public`, `made_for_kids` `false`, `notify_subscribers` `true`, `category_id` `27` (Education),
  `default_language` `ur`, `default_audio_language` `ur`, `tags`: 8–12 English/Roman Urdu/Urdu keywords
Then update `pending.json` to `{"stage":"uploaded","video_id":...}` and push.

## 10. Thumbnail
Wait ~4 minutes (the Short must finish processing), then one call: action `upload_video_thumbnail`
(tool_name `youtube_update_video_thumbnail`), `video_id`, `thumbnail` =
`https://raw.githubusercontent.com/aizaz6241/ezox-howitworks-shorts/media/thumb.jpg`.
If it fails, wait 4 more minutes and try once more; if it still fails, log `thumb: failed` (the next run retries via Resume).

## 11. Log and clean up
Append to `repo/log.json`: `{"date","topic","category","title","title_en","video_id","duration","voice","thumb"}`;
commit + push `main`. Then push `media` with `pending.json` deleted.

## Failure rules
- Retry a failed step once. Never upload a video that failed a check in step 7.
- ElevenLabs out of credits / key or plan rejected → skip the day (step 5 rule), never fall back to burning credits.
- Zapier/YouTube error twice (expired connection, Zapier task limit) → keep everything in `media` with
  `pending.json` so tomorrow's run uploads it without new credits; end with a message telling Aizaz exactly
  what to fix (e.g. "Zapier mein YouTube reconnect karein").
- Never write the API key into the repo, the log, a commit or any file.
- Final message: 3–4 lines in Roman Urdu — topic, YouTube link, duration — or what failed and what to fix.
