"""
Step 1 of 2 — build the prompts (no model calls, fast, cheap).

Reads:
    input/system_prompt.txt
    input/user_prompt.txt      (must contain <codes></codes> and
                                <transcript></transcript> placeholders)
    input/codes.txt
    transcripts/*.txt

Writes:
    prompts/_system_prompt.txt            -- shared across all transcripts
    prompts/<transcript_name>.user.txt    -- codes + transcript spliced in

Re-run this whenever you edit the codebook, the user prompt template, or
add/remove transcripts. After it finishes, run run_coding.py to call Ollama.
"""

from __future__ import annotations

import re

from config import (
    TRANSCRIPTS_DIR, PROMPTS_DIR,
    SYSTEM_PROMPT_FILE, USER_PROMPT_FILE, CODES_FILE, SYSTEM_PROMPT_OUT,
    read_text,
)


def _insert_between_tags(template: str, tag: str, payload: str) -> str:
    """
    Replace the block between <tag>...</tag> in `template` with `payload`.

    Works even if the template has whitespace/newlines between the tags.
    Raises if the tag pair is missing so mistakes are caught early.
    """
    pattern = re.compile(rf"(<{tag}>)(.*?)(</{tag}>)", flags=re.DOTALL)
    if not pattern.search(template):
        raise ValueError(f"Could not find <{tag}>...</{tag}> in the user prompt template.")
    # Use a lambda replacement so `payload` is treated as a literal string
    # (backreferences like \1 inside payload won't be misinterpreted).
    return pattern.sub(lambda m: f"{m.group(1)}\n{payload}\n{m.group(3)}", template)


def main() -> None:
    system_prompt = read_text(SYSTEM_PROMPT_FILE).strip()
    user_template = read_text(USER_PROMPT_FILE)
    codes_text    = read_text(CODES_FILE).strip()

    transcripts = sorted(p for p in TRANSCRIPTS_DIR.glob("*.txt") if p.is_file())
    if not transcripts:
        raise FileNotFoundError(f"No .txt transcripts found in {TRANSCRIPTS_DIR}")

    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    # System prompt is the same for every transcript — write once.
    SYSTEM_PROMPT_OUT.write_text(system_prompt, encoding="utf-8")

    for t_path in transcripts:
        transcript_text = read_text(t_path).strip()
        user_prompt = _insert_between_tags(user_template, "codes", codes_text)
        user_prompt = _insert_between_tags(user_prompt, "transcript", transcript_text)

        out_path = PROMPTS_DIR / f"{t_path.stem}.user.txt"
        out_path.write_text(user_prompt, encoding="utf-8")
        print(f"  wrote {out_path.name}  ({len(user_prompt):,} chars)")

    print(f"\nBuilt {len(transcripts)} user prompts -> {PROMPTS_DIR}")
    print(f"Shared system prompt        -> {SYSTEM_PROMPT_OUT}")


if __name__ == "__main__":
    main()
