"""Guard ElevenLabs credits before spending any.

    ELEVEN_API_KEY=... python3 credits.py --project <dir>

Counts the characters that tts_eleven.py would send for <project>/script.json and compares them with what
is left on the plan. Exit codes: 0 = go, 3 = not enough credits left (skip today, don't burn the rest),
4 = key rejected / plan problem, 5 = script too long (> 1100 chars ~ over 60 s: shorten it first).
Never exits 0 unless at least 1.3x the needed characters remain.
"""
import argparse, json, os, sys, urllib.error, urllib.request


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--project", required=True); a = ap.parse_args()
    key = os.environ.get("ELEVEN_API_KEY") or sys.exit("set ELEVEN_API_KEY")
    s = json.load(open(os.path.join(a.project, "script.json")))
    need = sum(len(l["spoken"]) for t in s["takes"] for l in t["lines"])
    if need > 1100:
        print(f"script is {need} chars (> 1100): shorten it"); sys.exit(5)
    try:
        req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": key})
        sub = json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        print(f"ElevenLabs refused the key: {e.code} {e.read()[:200]!r}"); sys.exit(4)
    left = sub["character_limit"] - sub["character_count"]
    print(json.dumps({"tier": sub.get("tier"), "status": sub.get("status"), "left": left, "need": need,
                      "resets_unix": sub.get("next_character_count_reset_unix")}))
    if sub.get("status") not in ("active", "trialing", None):
        sys.exit(4)
    if left < need * 1.3:
        sys.exit(3)


if __name__ == "__main__":
    main()
