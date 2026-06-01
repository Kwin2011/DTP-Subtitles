# DTP Subtitles — SRT Processor

A command-line tool for batch-processing `.srt` subtitle files.  
It wraps long subtitle lines to a target character limit using a semantic line-balancing algorithm, then splits any blocks exceeding two lines into separate timed sub-blocks.

---

## Requirements

- Python 3.10+
- [`pysrt`](https://github.com/byroot/pysrt)

```bash
pip install -r requirements.txt
```

---

## File Structure

```
project/
├── main.py               # Entry point
├── line_wrapper.py       # Core wrapping algorithm (Greedy + F1/F2/F3)
├── srt_processor.py      # Applies LineWrapper to every subtitle block
├── srt_splitter.py       # Splits 3+ line blocks into ≤2 line sub-blocks
├── processing_report.py  # Collects and prints change statistics
├── logger.py             # Separates console progress from detailed log file
└── requirements.txt
```

---

## Usage

```bash
# Interactive — prompts for directory
python main.py

# Explicit path
python main.py "C:\path\to\subtitles"

# Custom character limit
python main.py "C:\path\to\subtitles" --max-chars 42

# Show top 20 files in the final report
python main.py "C:\path\to\subtitles" --top 20

# Reset — restore all originals from .bak and exit
python main.py "C:\path\to\subtitles" --reset
```

### Options

| Option | Default | Description |
|---|---|---|
| `target_dir` | *(prompted)* | Root folder; all `.srt` files are found recursively |
| `--max-chars N` | `36` | Maximum characters allowed per subtitle line |
| `--top N` | `10` | Number of most-changed files shown in the final report |
| `--reset` | — | Restore every `.bak` → `.srt`, delete the `.bak`, and exit |

---

## File Strategy (Backup & Output)

The tool never silently overwrites your originals.

```
First run
  lecture.srt  ──copy──►  lecture.bak   (original, never touched again)
  lecture.bak  ──process──►  lecture.srt (result overwrites)

Subsequent runs
  lecture.bak exists  ──process──►  lecture.srt (re-processed from original)

Reset  (--reset)
  lecture.bak  ──copy──►  lecture.srt   (original restored)
  lecture.bak  deleted
```

- `.bak` always contains the **unmodified original**.
- `.srt` always contains the **latest processed result**.
- Running the tool again re-processes from `.bak`, so results are reproducible.

---

## Algorithm

Each subtitle block is a single flat string after cleaning.  
It passes through three stages:

### Stage 1 — Greedy Split

Words are packed left-to-right into lines until the character limit is reached.  
This produces an initial set of lines that respect the hard limit but may be unbalanced.

```
Input : "Vou dar instruções básicas sobre como examinar e pontuar pacientes"
Limit : 36
Lines : ["Vou dar instruções básicas sobre como", "examinar e pontuar pacientes"]
```

### Stage 2 — Balance by Average

The target number of lines `N` is calculated as `ceil(total_chars / limit)`.  
Words are moved from longer lines to the next line until every line is at or below `total_chars / N`.  
This distributes text evenly before semantic passes begin.

```
Before : ["Vou dar instruções básicas sobre como",  (37)
           "examinar e pontuar pacientes"]           (28)
After  : ["Vou dar instruções básicas sobre",        (32)
           "como examinar e pontuar pacientes"]       (33)
```

### Stage 3 — Semantic Passes (F1 / F2 / F3)

Applied to each consecutive pair of lines `(i, i+1)`:

#### F1 — Push overflow and fix orphans
1. **Technical**: if line `i` exceeds the limit, move its last word to line `i+1` until it fits.
2. **Semantic**:
   - If the last word is a single character (e.g. `"a"`, `"e"`), move it to the next line.
   - If the second-to-last word ends with punctuation (but not an enumeration like `"x, y, z"`), move the last word to the next line — keeping the clause together.

#### F2 — Pull from next line
Pulls the first word of line `i+1` into line `i` when all of these hold:
- The word is longer than 1 character.
- Line `i` does not end with punctuation.
- The word ends with sentence-ending punctuation (`.!?;`) **or** it is preceded by a comma/dash in the next line.
- The word fits within the remaining space on line `i`.

A contextual sub-rule moves a short trailing word (≤ 4 chars) back to the next line if the pulled word ended a sentence — preventing orphaned sentence starters.

#### F3 — Rebalance tail
Moves the last word of line `i` to line `i+1` in two situations:
- The last word ends with punctuation and the next line starts with a lowercase word (continuation) — *skip*; otherwise move if it fits.
- The length difference between line `i` and line `i+1` exceeds `1.5 × len(last_word)` — move to even out the visual balance.

### Stage 4 — Block Splitting (SRTSplitter)

After wrapping, any block with more than 2 lines is split into sub-blocks.  
Timecodes are redistributed proportionally by character weight:

```
block duration × (chars in sub-block / total chars in block)
```

Split strategy by line count:

| Lines | Strategy |
|---|---|
| ≤ 2 | No split |
| 3 | Try `[2+1]` and `[1+2]`; keep the one with the smaller weight imbalance |
| 4 | Split `[2+2]` |
| 5 | Try `[2+2+1]` and `[1+2+2]`; keep the lower imbalance |
| 6+ | Chunked `[2, 2, 2, …]` |

---

## Output

### Console — progress only

```
Target dir : C:\subtitles
Max chars  : 36
Log file   : srt_log_C__subtitles_20260601_143022.txt

Scanning for .srt files…
Found 12 file(s) to process.

[1/12] lecture_01.srt
    [bak] backup created → lecture_01.bak
    ✅ done — 54 blocks total, 38 block(s) rewrapped, 5 block(s) split
[2/12] lecture_02.srt
    [bak] backup found — using lecture_02.bak
    ✅ done — 61 blocks total, no changes
```

### Log file — full detail

A `.txt` log file is saved in the script directory, named:

```
srt_log_<sanitized_path>_<YYYYMMDD_HHMMSS>.txt
```

It contains for every file:
- Header with path and block count
- Each block marked as `✓` (unchanged), `↩` (rewrapped with before/after), or `✂` (split)
- Per-file summary: blocks rewrapped, unchanged, split, words moved, empty blocks removed

Followed by a final ranked report of the most-changed files:

```
======================================================================
  FINAL REPORT  —  top 10 most-changed files
======================================================================
  File                                   Empty Words Lines Split  Total
  -------------------------------------- ----- ----- ----- ----- ------
  lecture_05.srt                             2    47    31    12     92
  lecture_01.srt                             0    23    18     5     46
  ...
======================================================================
  Columns: Empty=removed empty blocks | Words=words moved between lines
           Lines=extra lines added    | Split=blocks split to ≤2 lines
======================================================================
```

---

## Modules

### `line_wrapper.py` — `LineWrapper`
Takes a flat string and a character limit. Returns `self.lines` (list of wrapped lines) and `self.words_moved_count` (total word transfers for reporting).

### `srt_processor.py` — `SRTProcessor`
Opens an `.srt` file with `pysrt`, runs `clean_text()` (flattens multi-line blocks, removes empty entries) and `split()` (applies `LineWrapper` to each subtitle). Accepts optional `report` and `logger` instances.

### `srt_splitter.py` — `SRTSplitter`
Reads the wrapped `.srt`, splits any block exceeding 2 lines, redistributes timecodes by character weight.

### `processing_report.py` — `ProcessingReport`
Accumulates per-file counters (`empty_blocks_removed`, `words_moved`, `lines_added`, `blocks_split`). Prints a ranked summary table to console and writes it to the log.

### `logger.py` — `Logger`
Single responsibility: all output goes through here. Console methods print progress; log methods write structured detail to the `.txt` file. Keeps `sys.stdout` clean.
