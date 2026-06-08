"""
Step 2 of 2 — send each prebuilt prompt to Ollama.

Reads:
    prompts/_system_prompt.txt
    prompts/*.user.txt          (produced by build_prompts.py)

Writes:
    output/<model_slug>/<transcript_name>.txt

Each model gets its own folder under output/ so you can code the same
transcripts with multiple models and compare. Edit MODEL and the sampling
parameters below, then run this script. Re-run with a different MODEL to
add another model's outputs alongside.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import ollama

from config import (
    INPUT_DIR, TRANSCRIPTS_DIR, PROMPTS_DIR, OUTPUT_DIR,
    SYSTEM_PROMPT_OUT, read_text,
)


# ---------------------------------------------------------------------------
# GLOBAL PARAMETERS  --  edit these to change the run
# ---------------------------------------------------------------------------

MODEL       = "gemma4:31b"    # e.g. "gemma3:4b", "gpt-oss:120b"
TEMPERATURE = 0.8             # 0.0 = deterministic, higher = more creative
TOP_P       = 0.9             # nucleus sampling
TOP_K       = 64              # top-k sampling
NUM_CTX     = 33000           # context window in tokens; longest prompt is ~20k tokens
SEED        = 42              # set to None for non-deterministic runs

# If True, skip transcripts whose output file already exists for this model.
SKIP_EXISTING = True

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_slug(model: str) -> str:
    """Turn 'gemma3:4b' into 'gemma3_4b' so it can be a folder name."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", model)


def _warn_if_prompts_stale() -> None:
    """
    Warn (but keep going) if anything in input/ or transcripts/ has been
    modified more recently than the oldest file in prompts/.
    """
    if not PROMPTS_DIR.exists():
        raise FileNotFoundError(
            f"{PROMPTS_DIR} does not exist. Run `python build_prompts.py` first."
        )

    prompt_files = list(PROMPTS_DIR.glob("*.user.txt"))
    if not prompt_files:
        raise FileNotFoundError(
            f"No prompts in {PROMPTS_DIR}. Run `python build_prompts.py` first."
        )

    oldest_prompt_mtime = min(p.stat().st_mtime for p in prompt_files)
    sources = list(INPUT_DIR.glob("*.txt")) + list(TRANSCRIPTS_DIR.glob("*.txt"))
    newer = [p for p in sources if p.stat().st_mtime > oldest_prompt_mtime]

    if newer:
        names = ", ".join(sorted(p.name for p in newer))
        print(
            "WARNING: these source files are newer than the built prompts:\n"
            f"  {names}\n"
            "  Consider running `python build_prompts.py` before continuing.\n"
        )


def _preflight_model_check() -> None:
    """
    Verify Ollama is reachable and MODEL is pulled, BEFORE we start looping.

    Without this, a missing model produces 17 identical ERROR files and wastes
    a few seconds per transcript waiting for each 404. We'd rather fail fast
    with a friendly hint.
    """
    try:
        ollama.show(MODEL)
    except ollama.ResponseError as e:
        status = getattr(e, "status_code", None)
        if status == 404 or "not found" in str(e).lower():
            raise SystemExit(
                f"ERROR: model '{MODEL}' is not pulled on this machine.\n"
                f"  Fix:      ollama pull {MODEL}\n"
                f"  Or:       edit MODEL at the top of run_coding.py to a model\n"
                f"            you already have. Run `ollama list` to see them."
            )
        raise
    except Exception as e:
        raise SystemExit(
            f"ERROR: could not reach Ollama ({type(e).__name__}: {e}).\n"
            f"  Is the Ollama server running?  Try:  ollama serve"
        )
    print(f"Preflight OK: model '{MODEL}' is available.\n")


def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    """One chat call to Ollama with the global sampling parameters."""
    options = {
        "temperature": TEMPERATURE,
        "top_p":       TOP_P,
        "top_k":       TOP_K,
        "num_ctx":     NUM_CTX,
    }
    if SEED is not None:
        options["seed"] = SEED

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        options=options,
    )
    return response["message"]["content"]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _warn_if_prompts_stale()
    _preflight_model_check()

    system_prompt = read_text(SYSTEM_PROMPT_OUT).strip()

    model_dir = OUTPUT_DIR / _model_slug(MODEL)
    model_dir.mkdir(parents=True, exist_ok=True)

    prompt_files = sorted(PROMPTS_DIR.glob("*.user.txt"))
    run_meta = {
        "model":       MODEL,
        "temperature": TEMPERATURE,
        "top_p":       TOP_P,
        "top_k":       TOP_K,
        "num_ctx":     NUM_CTX,
        "seed":        SEED,
    }

    for i, p_path in enumerate(prompt_files, start=1):
        transcript_name = p_path.name[: -len(".user.txt")]
        out_path = model_dir / f"{transcript_name}.txt"

        if SKIP_EXISTING and out_path.exists():
            print(f"[{i}/{len(prompt_files)}] SKIP {transcript_name} (exists)")
            continue

        print(f"[{i}/{len(prompt_files)}] Coding {transcript_name} with {MODEL} ...", flush=True)
        user_prompt = read_text(p_path)

        t0 = time.time()
        try:
            reply = _call_ollama(system_prompt, user_prompt)
        except Exception as e:
            err_path = model_dir / f"{transcript_name}.ERROR.txt"
            err_path.write_text(f"{type(e).__name__}: {e}\n", encoding="utf-8")
            print(f"    ERROR -> {err_path.name}")
            continue
        elapsed = time.time() - t0

        header = (
            "===== RUN METADATA =====\n"
            f"transcript : {transcript_name}\n"
            f"timestamp  : {datetime.now().isoformat(timespec='seconds')}\n"
            f"elapsed_s  : {elapsed:.1f}\n"
            f"params     : {json.dumps(run_meta)}\n"
            "========================\n\n"
        )
        out_path.write_text(header + reply, encoding="utf-8")
        print(f"    done in {elapsed:.1f}s -> {out_path.relative_to(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
