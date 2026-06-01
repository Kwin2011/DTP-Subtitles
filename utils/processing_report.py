import os
"""
Збирає статистику змін по кожному файлу і друкує підсумковий звіт.

Метрики:
  empty_blocks_removed  — порожніх блоків видалено (clean_text)
  words_moved           — слів перенесено між рядками (F1/F2/F3 в LineWrapper)
  lines_added           — рядків додано відносно вихідних блоків (wrapping)
  blocks_split          — блоків розбито на 2+ частини (SRTSplitter)
  total_changes         — сума всіх вище (для сортування)
"""

from dataclasses import dataclass, field


@dataclass
class FileStats:
    path: str
    empty_blocks_removed: int = 0
    words_moved: int = 0        # переноси слів між рядками
    lines_added: int = 0        # рядків більше ніж було блоків
    blocks_split: int = 0       # блоків, що були розбиті splitter-ом

    @property
    def total_changes(self) -> int:
        return (self.empty_blocks_removed
                + self.words_moved
                + self.lines_added
                + self.blocks_split)


class ProcessingReport:
    def __init__(self):
        self._stats: list[FileStats] = []
        self._current: FileStats | None = None

    # ------------------------------------------------------------------
    def begin_file(self, path: str):
        self._current = FileStats(path=path)
        self._stats.append(self._current)

    def _s(self) -> FileStats:
        assert self._current is not None, "Call begin_file() first"
        return self._current

    # ------------------------------------------------------------------
    # Методи для запису метрик з інших модулів
    # ------------------------------------------------------------------
    def add_empty_blocks(self, n: int):
        self._s().empty_blocks_removed += n

    def add_words_moved(self, n: int):
        self._s().words_moved += n

    def add_lines_added(self, n: int):
        self._s().lines_added += n

    def add_blocks_split(self, n: int):
        self._s().blocks_split += n

    # ------------------------------------------------------------------
    def print_summary(self, top_n: int = 10):
        if not self._stats:
            print("No files processed.")
            return

        ranked = sorted(self._stats, key=lambda s: s.total_changes, reverse=True)

        print("\n" + "=" * 70)
        print(f"  PROCESSING REPORT  —  top {min(top_n, len(ranked))} most-changed files")
        print("=" * 70)
        print(f"  {'File':<38} {'Empty':>5} {'Words':>5} {'Lines':>5} {'Split':>5} {'Total':>6}")
        print(f"  {'-'*38} {'-----':>5} {'-----':>5} {'-----':>5} {'-----':>5} {'------':>6}")

        for s in ranked[:top_n]:
            name = s.path if len(s.path) <= 38 else "…" + s.path[-37:]
            print(f"  {name:<38} {s.empty_blocks_removed:>5} {s.words_moved:>5} "
                  f"{s.lines_added:>5} {s.blocks_split:>5} {s.total_changes:>6}")

        print(f"  {'-'*38} {'-----':>5} {'-----':>5} {'-----':>5} {'-----':>5} {'------':>6}")
        totals = FileStats(path="TOTAL")
        for s in self._stats:
            totals.empty_blocks_removed += s.empty_blocks_removed
            totals.words_moved          += s.words_moved
            totals.lines_added          += s.lines_added
            totals.blocks_split         += s.blocks_split
        print(f"  {'TOTAL':<38} {totals.empty_blocks_removed:>5} {totals.words_moved:>5} "
              f"{totals.lines_added:>5} {totals.blocks_split:>5} {totals.total_changes:>6}")
        print("=" * 70)
        print("  Columns: Empty=removed empty blocks | Words=words moved between lines")
        print("           Lines=extra lines added    | Split=blocks split to ≤2 lines")
        print("=" * 70)

    def write_to_log(self, logger, top_n: int = 10):
        """Write the same summary table into the log file."""
        if not self._stats:
            return
        ranked = sorted(self._stats, key=lambda s: s.total_changes, reverse=True)

        logger.log("\n" + "=" * 70)
        logger.log(f"  FINAL REPORT  —  top {min(top_n, len(ranked))} most-changed files")
        logger.log("=" * 70)
        logger.log(f"  {'File':<38} {'Empty':>5} {'Words':>5} {'Lines':>5} {'Split':>5} {'Total':>6}")
        logger.log(f"  {'-'*38} {'-----':>5} {'-----':>5} {'-----':>5} {'-----':>5} {'------':>6}")

        for s in ranked[:top_n]:
            name = os.path.basename(s.path)
            name = name if len(name) <= 38 else "…" + name[-37:]
            logger.log(f"  {name:<38} {s.empty_blocks_removed:>5} {s.words_moved:>5} "
                       f"{s.lines_added:>5} {s.blocks_split:>5} {s.total_changes:>6}")

        totals = FileStats(path="TOTAL")
        for s in self._stats:
            totals.empty_blocks_removed += s.empty_blocks_removed
            totals.words_moved          += s.words_moved
            totals.lines_added          += s.lines_added
            totals.blocks_split         += s.blocks_split

        logger.log(f"  {'-'*38} {'-----':>5} {'-----':>5} {'-----':>5} {'-----':>5} {'------':>6}")
        logger.log(f"  {'TOTAL':<38} {totals.empty_blocks_removed:>5} {totals.words_moved:>5} "
                   f"{totals.lines_added:>5} {totals.blocks_split:>5} {totals.total_changes:>6}")
        logger.log("=" * 70)
