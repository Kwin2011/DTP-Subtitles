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

Output files (written next to each source file):
    <name>_processed.srt   after line-wrap pass
    <name>_split.srt       after 2-line block splitting

Already-processed files (*_processed.srt, *_split.srt) are skipped.
A detailed log file is saved in the script directory.
"""

import os
import argparse
from srt_processor import SRTProcessor
from srt_splitter import SRTSplitter
from processing_report import ProcessingReport
from logger import Logger

PROCESSED_SUFFIXES = ("_processed.srt", "_split.srt")


def is_already_processed(filename: str) -> bool:
    lower = filename.lower()
    return any(lower.endswith(s) for s in PROCESSED_SUFFIXES)


def collect_srt_files(root_dir: str, logger: Logger) -> list[str]:
    found = []
    skipped = []
    for dirpath, _dirs, files in os.walk(root_dir):
        for filename in files:
            if not filename.lower().endswith(".srt"):
                continue
            if is_already_processed(filename):
                skipped.append(filename)
                continue
            found.append(os.path.join(dirpath, filename))
    if skipped:
        logger.console(f"  Skipped {len(skipped)} already-processed file(s).")
    return found


def process_file(input_path: str, index: int, total: int,
                 max_chars: int, report: ProcessingReport,
                 logger: Logger) -> None:
    base, _ = os.path.splitext(input_path)
    output_processed = base + "_processed.srt"
    output_split     = base + "_split.srt"

    logger.console_file_start(input_path, index, total)
    logger.log_file_start(input_path)

    report.begin_file(input_path)

    # --- Step 1: clean ---
    processor = SRTProcessor(input_path)
    processor.clean_text(report=report, logger=logger)

    # --- Step 2: wrap lines ---
    processor.split(max_chars=max_chars, report=report, logger=logger)
    processor.stats(logger=logger)
    processor.save(output_processed)

    # --- Step 3: split blocks to max 2 lines ---
    splitter = SRTSplitter(output_processed)
    blocks_split = splitter.split_blocks(report=report, logger=logger)
    splitter.save(output_split)

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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.target_dir:
        args.target_dir = input("Target directory: ").strip().strip('"')

    if not os.path.isdir(args.target_dir):
        print(f"❌ Directory not found: {args.target_dir}")
        raise SystemExit(1)

    logger = Logger(target_dir=args.target_dir, max_chars=args.max_chars)
    log_path = logger.open()

    logger.console(f"Target dir : {args.target_dir}")
    logger.console(f"Max chars  : {args.max_chars}")
    logger.console(f"Log file   : {log_path}")
    logger.console("\nScanning for .srt files…")

    srt_files = collect_srt_files(args.target_dir, logger)

    if not srt_files:
        logger.console("No unprocessed .srt files found.")
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

    # --- Final report to console AND log ---
    report.print_summary(top_n=args.top)
    report.write_to_log(logger, top_n=args.top)

    logger.close()


if __name__ == "__main__":
    main()
