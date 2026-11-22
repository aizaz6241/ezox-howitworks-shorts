"""Burn Urdu (Nastaliq) captions onto a rendered vertical Short, timed to the spoken words.

    python3 urdu_captions.py --project <dir> --font NotoNastaliqUrdu.ttf --video in.mp4 --out out.mp4

Needs audio/timing.json (build_narration.py) and audio/word_times.json (tts_eleven.py).
Each line is split into chunks of up to 4 words (breaking after a comma when it can); a chunk
appears when its first word is spoken. The first line (the hook) is yellow, the rest white.
Also writes <out>.srt. Pillow with raqm shapes the Nastaliq correctly; libass here does not.
"""
import argparse, json, pathlib, re, subprocess, sys

from PIL import Image, ImageDraw, ImageFont, features

strip = lambda s: re.sub(r"[\s،۔؟,.!?ِ]", "", s)


def chunks(text, n=4):
    words = text.split(); out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= n or (w.endswith("،") and len(cur) >= 2):
            out.append(cur); cur = []
    if cur:
        if len(cur) == 1 and out: out[-1] += cur
        else: out.append(cur)
    return [" ".join(c).rstrip("،") for c in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True); ap.add_argument("--font", required=True)
    ap.add_argument("--video", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--y", type=int, default=1200)
    a = ap.parse_args()
    assert features.check("raqm"), "Pillow needs libraqm for Urdu shaping"
    proj = pathlib.Path(a.project)
    timing = json.load(open(proj / "audio/timing.json"))
    wt = json.load(open(proj / "audio/word_times.json"))
    ev = []
    for seg in timing["segments"]:
        L, E = seg["start"], seg["end"]; toks = wt.get(str(seg["id"]), [])
        ch = chunks(seg["vo"]); total = max(1, sum(len(strip(c)) for c in ch)); acc = 0; ti = 0; starts = []
        for k, c in enumerate(ch):
            guess = L + (E - L) * acc / total; first = strip(c.split()[0]); hit = None
            for j in range(ti, len(toks)):
                if strip(toks[j]["w"]) == first:
                    hit = L + toks[j]["t"]; ti = j + 1; break
            starts.append(L if k == 0 else (hit if hit is not None and abs(hit - guess) < 1.5 else guess))
            acc += len(strip(c))
        for k, c in enumerate(ch):
            b = starts[k + 1] if k + 1 < len(ch) else E + 0.15
            ev.append([starts[k] - 0.05, b - 0.05, c, seg["id"] == timing["segments"][0]["id"]])
    for k in range(len(ev) - 1):
        ev[k][1] = min(ev[k][1], ev[k + 1][0] - 0.01)
    capdir = proj / "out/caps"; capdir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype(a.font, 80, layout_engine=ImageFont.Layout.RAQM)
    for i, (s, e, x, hook) in enumerate(ev):
        size = 80
        while True:
            f = ImageFont.truetype(a.font, size, layout_engine=ImageFont.Layout.RAQM)
            im = Image.new("RGBA", (1080, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.text((543, 158), x, font=f, fill=(0, 0, 0, 150), anchor="mm", direction="rtl", stroke_width=9, stroke_fill=(0, 0, 0, 150))
            d.text((540, 150), x, font=f, fill=(255, 214, 60) if hook else (255, 255, 255), anchor="mm", direction="rtl",
                   stroke_width=7, stroke_fill=(0, 0, 0))
            bb = im.getbbox()
            if (bb[0] > 30 and bb[2] < 1050) or size <= 56: break
            size -= 6
        im.save(capdir / f"c{i:02d}.png")
    inputs, chain, last = ["-i", a.video], [], "0:v"
    for i, (s, e, _, _) in enumerate(ev):
        inputs += ["-i", str(capdir / f"c{i:02d}.png")]
        chain.append(f"[{last}][{i + 1}:v]overlay=0:{a.y}:enable='between(t,{max(0, s):.3f},{e:.3f})'[v{i}]"); last = f"v{i}"
    tmp = str(pathlib.Path(a.out).with_suffix(".tmp.mp4"))
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(chain), "-map", f"[{last}]",
                        "-map", "0:a", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", "-movflags", "+faststart", tmp])
    if r.returncode: sys.exit(r.returncode)
    pathlib.Path(tmp).rename(a.out)

    def st(x):
        ms = int(round(max(0, x) * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
    pathlib.Path(a.out).with_suffix(".srt").write_text(
        "\n".join(f"{i+1}\n{st(s)} --> {st(e)}\n{x}\n" for i, (s, e, x, _) in enumerate(ev)), encoding="utf8")
    print(f"captions: {len(ev)} -> {a.out}")


if __name__ == "__main__":
    main()
