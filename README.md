This is an on overview. See Technical Appendix 1.pdf for more details.

# LC Coding — Qualitative Interview Coding with Ollama

Two small Python scripts that use a local [Ollama](https://ollama.com) model to apply a predefined codebook to qualitative interview transcripts.

The pipeline is split into two steps so you only build prompts once and can then run as many models over them as you like:

1. **`build_prompts.py`** — reads the templates and transcripts, splices them together, and writes one prompt file per transcript to `prompts/`. Fast, no model calls, re-run only when inputs change.
2. **`run_coding.py`** — sends each prebuilt prompt to Ollama and saves the model's reply to `output/<model>/`. Run once per model you want to try.

A tiny `config.py` holds the shared paths.

---

## Folder layout

```
LC_coding/
├── config.py                  # shared paths + file-reading helper
├── build_prompts.py           # step 1 — run once, or when inputs change
├── run_coding.py              # step 2 — run once per model
├── README.md
├── input/
│   ├── system_prompt.txt      # the system prompt (role / persona)
│   ├── user_prompt.txt        # main instructions; must contain
│   │                          # <codes></codes> and <transcript></transcript>
│   └── codes.txt              # the codebook (code names + definitions)
├── transcripts/               # one .txt per interview — all are coded
│   ├── JaneDoe_AI.txt
│   ├── JohnDoe_AI.txt
│   └── ...
├── prompts/                   # produced by build_prompts.py
│   ├── _system_prompt.txt     # shared across all transcripts
│   ├── JaneDoe_AI.user.txt
│   └── ...
└── output/                    # produced by run_coding.py — one folder per model
    ├── gemma3_4b/
    │   ├── JaneDoe_AI.txt
    │   └── ...
    └── llama3.1_8b/
        └── ...
```

---

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com) installed and running locally
- The `ollama` Python package: `pip install ollama`
- At least one model pulled locally: `ollama pull gemma3:4b`

---

## Quick start

```bash
# 1. Install the Python client
pip install ollama

# 2. Start the Ollama server (in a separate terminal if not already running)
ollama serve

# 3. Pull whatever model you want to try
ollama pull gemma3:4b

# 4. Build the prompts once (fast, no model calls)
python build_prompts.py

# 5. Run the coding (this is the slow step — it calls the model)
python run_coding.py
```

Re-run step 4 only when you change the codebook, the user prompt template, or add/remove transcripts. `run_coding.py` prints a warning at the top if it detects source files newer than the prompts.

On subsequent runs of `run_coding.py`, transcripts already coded by the current model are skipped — set `SKIP_EXISTING = False` at the top of the script to force re-coding.

---

## Global parameters

All tunable parameters for inference live at the top of `run_coding.py`. Edit them and re-run.

| Name | Default | What it does |
|---|---|---|
| `MODEL` | `"gemma3:4b"` | Ollama model tag. Try `gemma3:12b`, `llama3.1:8b`, `qwen2.5:14b`, etc. |
| `TEMPERATURE` | `0.2` | Lower = more deterministic, more faithful to instructions. |
| `TOP_P` | `0.9` | Nucleus sampling cutoff. |
| `TOP_K` | `40` | Top-k sampling cutoff. |
| `NUM_CTX` | `32768` | Context window in tokens. Longest prompt is ~20k tokens; lower this if you run out of VRAM. Some models don't support 32k+ context. |
| `SEED` | `42` | Fixed seed for reproducibility. Set to `None` for non-deterministic runs. |
| `SKIP_EXISTING` | `True` | Skip transcripts already coded by this model. |

Paths are defined in `config.py`.

---

## Trying multiple models

Because each model writes into its own folder under `output/`, comparing models is just a matter of editing `MODEL` and re-running:

```bash
# edit MODEL = "gemma3:4b" at top of run_coding.py, then:
python run_coding.py

# edit MODEL = "llama3.1:8b", then:
python run_coding.py

# edit MODEL = "qwen2.5:14b", then:
python run_coding.py
```

You'll end up with:
```
output/gemma3_4b/JaneDoe_AI.txt
output/llama3.1_8b/JaneDoe_AI.txt
output/qwen2.5_14b/JaneDoe_AI.txt
```

All three models see the exact same prompts — the `prompts/` folder is built once and reused.

---

## Customizing the prompts

- **System prompt** — edit `input/system_prompt.txt`. This sets the model's role.
- **User prompt / instructions** — edit `input/user_prompt.txt`. It *must* contain `<codes></codes>` and `<transcript></transcript>` tags; `build_prompts.py` will error early if either is missing.
- **Codebook** — edit `input/codes.txt`. Any format works; the file is inserted verbatim.

After any of these changes, re-run `python build_prompts.py`.

---

## Adding / removing transcripts

Drop more `.txt` files into `transcripts/` and re-run `build_prompts.py`. Remove files to stop coding them. No code changes needed.

---

## Output format

Each file in `output/<model>/` looks like:

```
===== RUN METADATA =====
transcript : JaneDoe_AI
timestamp  : 2026-04-24T21:05:00
elapsed_s  : 42.3
params     : {"model": "gemma3:4b", "temperature": 0.2, ...}
========================

-Paragraph: ...
-Primary code: ...
-Secondary code(s): ...
-Justification: ...
-Evidence: ...
-Confidence: ...
```

The body after the header is whatever the model returned. The shape of that body is controlled by `input/user_prompt.txt`, so adjust that file (and re-run `build_prompts.py`) if you want a different structure.

---

## Troubleshooting

**`Could not find <codes>...</codes> in the user prompt template.`**
The tags are missing from `input/user_prompt.txt`. Add them where you want the codebook inserted, then re-run `build_prompts.py`.

**`WARNING: these source files are newer than the built prompts`** (on run_coding.py startup)
Something in `input/` or `transcripts/` was edited after the last prompt build. Run `python build_prompts.py` to regenerate, then run `run_coding.py` again. The warning does not abort the run — it's just a reminder.

**`prompts/ does not exist` or `No prompts in prompts/`.**
You haven't built the prompts yet. Run `python build_prompts.py` first.

**Model returns truncated output or complains about context length.**
Lower `NUM_CTX` if VRAM is the problem, or raise it if the input is being truncated. Some models don't support 32k+ context — check the model card on [ollama.com/library](https://ollama.com/library).

**Connection refused / `ollama` errors.**
Make sure `ollama serve` is running and the model has been pulled with `ollama pull <model>`.

**Non-UTF-8 characters in transcripts.**
The scripts read files tolerantly (UTF-8, then cp1252, then replacement), so smart quotes and odd bytes won't crash them. If you see replacement characters in the output, the source file has stray bytes — open it in an editor, re-save as UTF-8, and re-run.

**Want to re-code everything for the current model?**
Delete the corresponding `output/<model>/` folder, or set `SKIP_EXISTING = False` at the top of `run_coding.py`.
