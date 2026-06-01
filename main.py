"""
SRT Subtitle Processor
======================
Processes .srt files in a directory tree:
  1. Cleans and wraps subtitle text (F1/F2/F3 algorithm)
  2. Splits blocks exceeding 2 lines proportionally by character weight

Usage:
    python main.py [target_dir] [--max-chars N] [--top N]

Options:
    --max-chars N   Max characters per subtitle line (default: 36)
    --top N         Files to show in final report (default: 10)

File strategy:
    - If <name>.bak exists  → process it, overwrite <name>.srt
    - If <name>.bak missing → copy <name>.srt to <name>.bak, then process
    .bak always holds the original; .srt always holds the result.
"""

import os
import shutil
import argparse
from core.srt_processor import SRTProcessor
from core.srt_splitter import SRTSplitter
from utils.processing_report import ProcessingReport
from utils.logger import Logger


def ensure_backup(srt_path: str, logger: Logger) -> str:
    """
    Ensure a .bak backup exists for srt_path.
    Returns the path to the source file that should be processed (.bak).
    """
    bak_path = os.path.splitext(srt_path)[0] + ".bak"
    if os.path.exists(bak_path):
        logger.console(f"    [bak] backup found — using {os.path.basename(bak_path)}")
    else:
        shutil.copy2(srt_path, bak_path)
        logger.console(f"    [bak] backup created → {os.path.basename(bak_path)}")
    return bak_path


def collect_srt_files(root_dir: str, logger: Logger) -> list[str]:
    """Return all .srt files (excluding .bak-like names, none here)."""
    found = []
    for dirpath, _dirs, files in os.walk(root_dir):
        for filename in sorted(files):
            if filename.lower().endswith(".srt"):
                found.append(os.path.join(dirpath, filename))
    return found


def process_file(srt_path: str, index: int, total: int,
                 max_chars: int, report: ProcessingReport,
                 logger: Logger) -> None:

    logger.console_file_start(srt_path, index, total)
    logger.log_file_start(srt_path)
    report.begin_file(srt_path)

    # --- Backup logic ---
    source_path = ensure_backup(srt_path, logger)   # always process from .bak

    # --- Step 1: clean ---
    processor = SRTProcessor(source_path)
    processor.clean_text(report=report, logger=logger)

    # --- Step 2: wrap lines ---
    processor.split(max_chars=max_chars, report=report, logger=logger)
    processor.stats(logger=logger)

    # Save wrapped result to a temp file so splitter can read it
    tmp_path = srt_path + ".tmp"
    processor.save(tmp_path)

    # --- Step 3: split blocks to max 2 lines ---
    splitter = SRTSplitter(tmp_path)
    blocks_split = splitter.split_blocks(report=report, logger=logger)

    # Overwrite the original .srt with final result
    splitter.save(srt_path)

    # Clean up temp file
    os.remove(tmp_path)

    # --- Per-file summary to log ---
    changed   = getattr(logger, "_proc_changed", 0)
    unchanged = getattr(logger, "_proc_unchanged", 0)
    words     = getattr(logger, "_proc_words_moved", 0)
    empty     = report._current.empty_blocks_removed
    logger.log_file_summary(
        changed=changed,
        unchanged=unchanged,
        split=blocks_split,
        words_moved=words,
        empty_removed=empty,
    )
    logger.console_file_done(
        blocks=changed + unchanged,
        changed=changed,
        split=blocks_split,
    )



def reset_backups(root_dir: str) -> None:
    """Restore every .bak file back to .srt, overwriting the current .srt."""
    print(f"\nResetting backups in: {root_dir}")
    restored = 0
    for dirpath, _dirs, files in os.walk(root_dir):
        for filename in sorted(files):
            if not filename.lower().endswith(".bak"):
                continue
            bak_path = os.path.join(dirpath, filename)
            srt_path = os.path.splitext(bak_path)[0] + ".srt"
            shutil.copy2(bak_path, srt_path)
            os.remove(bak_path)
            print(f"  ✅ {filename}  →  {os.path.basename(srt_path)}  (backup removed)")
            restored += 1
    if restored:
        print(f"\nDone. {restored} file(s) restored.")
    else:
        print("No .bak files found — nothing to reset.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-process SRT subtitle files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("target_dir", nargs="?", default=None,
                        help="Root directory with .srt files (recursive)")
    parser.add_argument("--max-chars", type=int, default=36, metavar="N",
                        help="Max chars per line (default: 36)")
    parser.add_argument("--top", type=int, default=10, metavar="N",
                        help="Files in final report (default: 10)")
    parser.add_argument("--reset", action="store_true",
                        help="Restore all .bak files back to .srt and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.target_dir:
        args.target_dir = input("Target directory: ").strip().strip('"')

    if not os.path.isdir(args.target_dir):
        print(f"❌ Directory not found: {args.target_dir}")
        raise SystemExit(1)

    if args.reset:
        reset_backups(args.target_dir)
        return

    logger = Logger(target_dir=args.target_dir, max_chars=args.max_chars)
    log_path = logger.open()

    logger.console(f"Target dir : {args.target_dir}")
    logger.console(f"Max chars  : {args.max_chars}")
    logger.console(f"Log file   : {log_path}")
    logger.console("\nScanning for .srt files…")

    srt_files = collect_srt_files(args.target_dir, logger)

    if not srt_files:
        logger.console("No .srt files found.")
        logger.close()
        return

    logger.console(f"Found {len(srt_files)} file(s) to process.")

    report = ProcessingReport()

    for i, path in enumerate(srt_files, start=1):
        try:
            process_file(path, index=i, total=len(srt_files),
                         max_chars=args.max_chars, report=report, logger=logger)
        except Exception as e:
            logger.console_error(f"Failed on {os.path.basename(path)}: {e}")
            logger.log(f"\n  [ERROR] {e}\n")

    logger.console(f"\nAll done. Processed {len(srt_files)} file(s).")
    logger.console(f"Log saved  : {log_path}")

    report.print_summary(top_n=args.top)
    report.write_to_log(logger, top_n=args.top)

    logger.close()


if __name__ == "__main__":
    main()