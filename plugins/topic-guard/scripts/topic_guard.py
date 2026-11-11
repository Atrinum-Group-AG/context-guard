#!/usr/bin/env python3
"""UserPromptSubmit hook: stop a session from silently growing too large.

Only the context size counts. When the last API call carried >= BLOCK_CTX tokens the
prompt is blocked once: type /clear for a fresh session (the old one stays in
/resume) or resend the prompt starting with "+" to continue. After a "+" pass
the guard stays quiet in that session until it grows another STEP_CTX tokens.
Tune through environment variables in settings.json.
"""
import json, os, sys

BLOCK_CTX = int(os.environ.get("TOPIC_GUARD_BLOCK_CTX", "200000"))
STEP_CTX = int(os.environ.get("TOPIC_GUARD_STEP_CTX", "100000"))
_DATA = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] and "${" not in sys.argv[1] else os.path.expanduser("~/.claude")
os.makedirs(_DATA, exist_ok=True)
STATE = os.path.join(_DATA, "topic_guard_state.json")


def last_ctx(path):
    """Context tokens of the last main-thread API call in the transcript."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 2_000_000))
            lines = f.read().decode("utf-8", "ignore").splitlines()
    except OSError:
        return 0
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        u = (d.get("message") or {}).get("usage") if d.get("type") == "assistant" else None
        if u and not d.get("isSidechain"):
            return (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) \
                + (u.get("cache_creation_input_tokens") or 0)
    return 0


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(s):
    s = dict(list(s.items())[-200:])  # keep the file small
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE)


def main():
    data = json.load(sys.stdin)
    prompt = (data.get("prompt") or "").lstrip()
    if prompt.startswith("/"):
        return  # slash commands always pass
    ctx = last_ctx(data.get("transcript_path") or "")
    sid = data.get("session_id") or data.get("transcript_path") or "?"
    state = load_state()
    if prompt.startswith("+"):
        if ctx >= BLOCK_CTX:
            state[sid] = ctx  # deliberate continuation: quiet until +STEP_CTX
            save_state(state)
        return
    passed_at = state.get(sid)
    limit = BLOCK_CTX if passed_at is None else max(BLOCK_CTX, passed_at + STEP_CTX)
    if ctx >= limit:
        print(json.dumps({
            "decision": "block",
            "reason": (f"Topic guard: this session holds {ctx // 1000}k tokens. "
                       "New topic? Type /clear and send it again (old session stays in /resume). "
                       "Same topic? Resend it starting with '+'."),
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never break prompting because of the guard
