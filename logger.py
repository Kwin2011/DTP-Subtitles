"""
Logger — розділяє консольний вивід і детальний лог-файл.

Консоль:  лише прогрес (файл, блок, done/warn/error)
Лог-файл: детальний запис кожної зміни (було → стало, які слова перенесено)
"""

import os
import sys
from datetime import datetime


class Logger:
    def __init__(self, target_dir: str, max_chars: int):
        self._f = None
        self._target_dir = target_dir
        self._max_chars = max_chars

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------
    def open(self) -> str:
        """Create log file and write header. Returns log path."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # sanitize target path into a short filename fragment
        safe = self._target_dir.replace("\\", "_").replace("/", "_")
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in safe)
        safe = safe.strip("_")[:60]
        filename = f"srt_log_{safe}_{ts}.txt"
        log_dir = os.path.dirname(os.path.abspath(__file__))
        self._path = os.path.join(log_dir, filename)
        self._f = open(self._path, "w", encoding="utf-8")
        self._write_header()
        return self._path

    def close(self):
        if self._f:
            self._f.write("\n" + "=" * 70 + "\n")
            self._f.write(f"  Log closed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._f.write("=" * 70 + "\n")
            self._f.close()
            self._f = None

    # ------------------------------------------------------------------
    # Console helpers (always go to stdout)
    # ------------------------------------------------------------------
    def console(self, msg: str):
        print(msg)

    def console_file_start(self, path: str, index: int, total: int):
        name = os.path.basename(path)
        print(f"\n[{index}/{total}] {name}")

    def console_file_done(self, blocks: int, changed: int, split: int):
        parts = []
        if changed:
            parts.append(f"{changed} block(s) rewrapped")
        if split:
            parts.append(f"{split} block(s) split")
        summary = ", ".join(parts) if parts else "no changes"
        print(f"    ✅ done — {blocks} blocks total, {summary}")

    def console_warn(self, msg: str):
        print(f"    ⚠️  {msg}")

    def console_error(self, msg: str):
        print(f"    ❌ {msg}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Log-file helpers (only go to file)
    # ------------------------------------------------------------------
    def log(self, msg: str):
        if self._f:
            self._f.write(msg + "\n")

    def log_file_start(self, path: str):
        self._f.write("\n")
        self._f.write("┌" + "─" * 68 + "┐\n")
        self._f.write(f"│  FILE: {path:<60}│\n")
        self._f.write("└" + "─" * 68 + "┘\n")

    def log_file_stats(self, removed_empty: int, total_blocks: int):
        if removed_empty:
            self._f.write(f"  [clean] {removed_empty} empty block(s) removed\n")
        self._f.write(f"  [info]  {total_blocks} block(s) to process\n")

    def log_block_unchanged(self, index: int, text: str):
        """Block fit in one line, no wrapping needed."""
        self._f.write(f"\n  #{index:>3}  ✓  {text}\n")

    def log_block_changed(self, index: int, original: str, lines: list[str],
                          words_moved: int):
        """Block was rewrapped — show before/after."""
        self._f.write(f"\n  #{index:>3}  ↩  BEFORE: {original}\n")
        for i, line in enumerate(lines, 1):
            marker = "         AFTER: " if i == 1 else "               "
            bar = "█" * min(len(line), self._max_chars) + ("▓" * (len(line) - self._max_chars) if len(line) > self._max_chars else "")
            self._f.write(f"        {marker}{line}  [{len(line)}]\n")
        if words_moved:
            self._f.write(f"               ({words_moved} word move(s))\n")

    def log_block_split(self, original_index: int, parts: list[list[str]]):
        """Block was split by SRTSplitter."""
        self._f.write(f"\n  #{original_index:>3}  ✂  split into {len(parts)} sub-block(s):\n")
        for i, part in enumerate(parts, 1):
            self._f.write(f"               part {i}: {' / '.join(part)}\n")

    def log_file_summary(self, changed: int, unchanged: int, split: int,
                         words_moved: int, empty_removed: int):
        self._f.write("\n  " + "─" * 60 + "\n")
        self._f.write(f"  Summary:\n")
        self._f.write(f"    Blocks rewrapped : {changed}\n")
        self._f.write(f"    Blocks unchanged : {unchanged}\n")
        self._f.write(f"    Blocks split     : {split}\n")
        self._f.write(f"    Words moved      : {words_moved}\n")
        if empty_removed:
            self._f.write(f"    Empty removed    : {empty_removed}\n")
        self._f.write("  " + "─" * 60 + "\n")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _write_header(self):
        self._f.write("=" * 70 + "\n")
        self._f.write("  SRT SUBTITLE PROCESSOR — DETAILED LOG\n")
        self._f.write("=" * 70 + "\n")
        self._f.write(f"  Target : {self._target_dir}\n")
        self._f.write(f"  Limit  : {self._max_chars} chars/line\n")
        self._f.write(f"  Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self._f.write("=" * 70 + "\n")
