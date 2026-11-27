"""Urdu voice for one Short, line by line, with ElevenLabs (word timings included).

    ELEVEN_API_KEY=... python3 tts_eleven.py --project <dir> [--voice ID] [--model eleven_v4]

Default voice: Aizaz (the owner's own cloned voice). Falls back to Saira if the clone is gone, and to
the premade George voice if the plan refuses paid voices.

Reads <project>/script.json (takes -> lines with "spoken"), writes:
  audio/lines/segNN.wav       one trimmed clip per line (48 kHz mono)
  audio/segments.json         what build_narration.py expects
  audio/word_times.json       {line_id: [{"w": word, "t": seconds from clip start}]}
Then run the skill's build_narration.py --project <dir>.
"""
import argparse, base64, json, os, pathlib, subprocess, sys, time, urllib.error, urllib.request, wave

import numpy as np

AIZAZ = "s4UUaKxuBYSzNp8rr3tk"      # Aizaz - the channel owner's own cloned Urdu voice (male); default since 2026-11-27
SAIRA = "hA0RyxVmITMttngSpcOF"      # Saira - Rich, Poetic Urdu Storyteller (needs a paid plan via API)
FALLBACK = "JBFqnCBsd6RMkjVDRZzb"   # George (premade; works on the free plan)
SR = 48000


def tts(key, voice, model, text, prev_text=None, next_text=None):
    body = {"text": text, "model_id": model, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    if prev_text: body["previous_text"] = prev_text
    if next_text: body["next_text"] = next_text
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128"
    for attempt in range(4):
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            msg = e.read()[:400].decode("utf8", "replace")
            if e.code in (400, 422) and ("previous_text" in body or "next_text" in body):
                body.pop("previous_text", None); body.pop("next_text", None); continue
            if e.code in (402, 401):
                raise RuntimeError(f"ELEVEN {e.code}: {msg}")
            if attempt == 3:
                raise RuntimeError(f"ELEVEN {e.code}: {msg}")
        except urllib.error.URLError:
            if attempt == 3: raise
        time.sleep(3 * (attempt + 1))


def decode(mp3_bytes):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-ar", str(SR), "-ac", "1", "-f", "f32le", "-"],
                       input=mp3_bytes, capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def trim(a, thr_db=-46, pad=0.04):
    hop = int(0.01 * SR); thr = 10 ** (thr_db / 20)
    env = np.array([np.abs(a[k:k + hop]).max() for k in range(0, len(a), hop)]) if len(a) else np.zeros(1)
    on = np.where(env > thr)[0]
    if len(on) == 0: return a, 0.0
    i0 = max(0, on[0] * hop - int(pad * SR)); i1 = min(len(a), (on[-1] + 1) * hop + int(pad * SR))
    c = a[i0:i1].copy(); f = int(0.008 * SR)
    c[:f] *= np.linspace(0, 1, f); c[-f:] *= np.linspace(1, 0, f)
    return c, i0 / SR


def word_times(text, alignment, offset):
    chars = alignment["characters"]; starts = alignment["character_start_times_seconds"]
    out, i, cur, t0 = [], 0, "", None
    for ch, st in zip(chars, starts):
        if ch.isspace():
            if cur: out.append({"w": cur, "t": round(max(0.0, t0 - offset), 3)})
            cur, t0 = "", None
        else:
            if t0 is None: t0 = st
            cur += ch
    if cur: out.append({"w": cur, "t": round(max(0.0, t0 - offset), 3)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--voice", default=AIZAZ)
    ap.add_argument("--model", default="eleven_v4")
    a = ap.parse_args()
    key = os.environ.get("ELEVEN_API_KEY") or sys.exit("set ELEVEN_API_KEY")
    proj = pathlib.Path(a.project)
    script = json.load(open(proj / "script.json"))
    (proj / "audio/lines").mkdir(parents=True, exist_ok=True)
    flat = [(take["take"], l, li == len(take["lines"]) - 1) for take in script["takes"] for li, l in enumerate(take["lines"])]
    voice = a.voice
    segs, wt = [], {}
    for k, (take, l, last) in enumerate(flat):
        prev_t = flat[k - 1][1]["spoken"] if k else None
        next_t = flat[k + 1][1]["spoken"] if k + 1 < len(flat) else None
        try:
            d = tts(key, voice, a.model, l["spoken"], prev_t, next_t)
        except RuntimeError as e:
            if voice == AIZAZ and ("404" in str(e) or "voice_not_found" in str(e)):
                print("Aizaz's cloned voice not found on this account -> falling back to Saira", file=sys.stderr)
                return main_with_voice(a, SAIRA)
            if "402" in str(e) and voice != FALLBACK:
                print("paid voice refused on this plan -> falling back to premade voice for the whole Short", file=sys.stderr)
                voice = FALLBACK
                return main_with_voice(a, voice)
            raise
        audio = decode(base64.b64decode(d["audio_base64"]))
        clip, off = trim(audio)
        with wave.open(str(proj / f"audio/lines/seg{l['id']:02d}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(clip, -1, 1) * 32767).astype(np.int16).tobytes())
        wt[str(l["id"])] = word_times(l["spoken"], d["alignment"], off)
        gap = l.get("gap_after", 0.35 if k == 0 else (0.3 if last else 0.18))
        segs.append({"id": l["id"], "scene": take, "caption": l["text"], "vo": l["spoken"], "gap_after": gap})
        print(f"line {l['id']}: {len(clip) / SR:.2f}s")
    json.dump({"segments": segs}, open(proj / "audio/segments.json", "w"), ensure_ascii=False, indent=1)
    json.dump(wt, open(proj / "audio/word_times.json", "w"), ensure_ascii=False, indent=0)
    json.dump({"voice": voice, "model": a.model}, open(proj / "audio/voice_used.json", "w"))


def main_with_voice(a, voice):
    sys.argv = [sys.argv[0], "--project", a.project, "--voice", voice, "--model", a.model]
    return main()


if __name__ == "__main__":
    main()
