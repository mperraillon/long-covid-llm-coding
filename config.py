"""
Shared configuration for build_prompts.py and run_coding.py.

Only paths and a file-reading helper live here. Sampling / model parameters
live at the top of run_coding.py so you can edit them without touching this
file.
"""

from pathlib import Path


# Paths are resolved relative to this file so the scripts work from any cwd.
BASE_DIR        = Path(__file__).resolve().parent
INPUT_DIR       = BASE_DIR / "input"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
PROMPTS_DIR     = BASE_DIR / "prompts"
OUTPUT_DIR      = BASE_DIR / "output"

SYSTEM_PROMPT_FILE = INPUT_DIR / "system_prompt.txt"
USER_PROMPT_FILE   = INPUT_DIR / "user_prompt.txt"
CODES_FILE         = INPUT_DIR / "codes.txt"

# The system prompt is the same for every transcript, so build_prompts.py
# writes one copy here and run_coding.py reads it back.
SYSTEM_PROMPT_OUT = PROMPTS_DIR / "_system_prompt.txt"


def read_text(path: Path) -> str:
    """
    Read a text file tolerantly.

    Some transcripts / prompts contain Windows-1252 smart quotes or stray
    bytes that are not valid UTF-8. Try UTF-8 first, then cp1252, and fall
    back to UTF-8 with replacement so we never crash on a bad byte.
    """
    data = path.read_bytes()
    for enc in ("utf-8", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
