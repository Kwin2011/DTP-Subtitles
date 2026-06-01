import pysrt
from core.line_wrapper import LineWrapper


class SRTProcessor:

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.subs = pysrt.open(file_path, encoding="utf-8")

    def clean_text(self, report=None, logger=None):
        """Remove extra line breaks and drop entirely empty subtitle blocks."""
        for sub in self.subs:
            sub.text = sub.text.replace("\n", " ").strip()

        before = len(self.subs)
        self.subs = pysrt.SubRipFile([
            sub for sub in self.subs if sub.text.strip()
        ])
        for i, sub in enumerate(self.subs, start=1):
            sub.index = i

        removed = before - len(self.subs)
        if removed:
            if report:
                report.add_empty_blocks(removed)
            if logger:
                logger.log_file_stats(removed_empty=removed,
                                      total_blocks=len(self.subs))
        else:
            if logger:
                logger.log_file_stats(removed_empty=0,
                                      total_blocks=len(self.subs))

    def split(self, max_chars: int = 50, debug: bool = False,
              report=None, logger=None):
        """Wrap each subtitle through LineWrapper and record changes."""

        changed = 0
        unchanged = 0
        total_words_moved = 0

        for sub in self.subs:
            text = sub.text.strip()
            if not text:
                continue

            wrapper = LineWrapper(text, limit=max_chars, debug=debug)

            is_changed = (len(wrapper.lines) > 1
                          or wrapper.words_moved_count > 0)

            if is_changed:
                changed += 1
                total_words_moved += wrapper.words_moved_count
                if logger:
                    logger.log_block_changed(
                        index=sub.index,
                        original=text,
                        lines=wrapper.lines,
                        words_moved=wrapper.words_moved_count,
                    )
            else:
                unchanged += 1
                if logger:
                    logger.log_block_unchanged(sub.index, text)

            if report:
                extra_lines = len(wrapper.lines) - 1
                if extra_lines > 0:
                    report.add_lines_added(extra_lines)
                report.add_words_moved(wrapper.words_moved_count)

            sub.text = "\n".join(wrapper.lines)

        if logger:
            # summary written later in main after splitter runs
            logger._proc_changed = changed
            logger._proc_unchanged = unchanged
            logger._proc_words_moved = total_words_moved

    def save(self, output_path: str):
        self.subs.save(output_path, encoding="utf-8")

    def stats(self, logger=None):
        total_lines = 0
        total_chars = 0
        for sub in self.subs:
            lines = sub.text.split("\n")
            total_lines += len(lines)
            total_chars += sum(len(l) for l in lines)
        avg = total_chars / total_lines if total_lines else 0
        if logger:
            logger.log(f"  [stats] {total_lines} lines, "
                       f"{total_chars} chars, avg {avg:.1f} chars/line")
