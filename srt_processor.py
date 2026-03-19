import sys
import pysrt
from line_wrapper import LineWrapper


class SRTProcessor:
    COLORS = {
        "F1": "\033[94m",   # blue
        "F2": "\033[92m",   # green
        "F3": "\033[93m",   # yellow
        "END": "\033[0m",   # reset
    }

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.subs = pysrt.open(file_path, encoding="utf-8")

    def clean_text(self):
        """Remove extra line breaks."""
        for sub in self.subs:
            sub.text = sub.text.replace("\n", " ").strip()

    def split(self, max_chars: int = 50, debug: bool = False, log_file: str = None):
        """Processing via LineWrapper (F1, F2, F3) with colored logs"""
        # Prepare log file
        if log_file:
            f = open(log_file, "w", encoding="utf-8")

            class Tee:
                def __init__(self, *files):
                    self.files = files

                def write(self, data):
                    for file in self.files:
                        file.write(data)

                def flush(self):
                    for file in self.files:
                        file.flush()

            sys.stdout = Tee(sys.stdout, f)

        print(f"\n{'=' * 70}")
        print(f"SUBTITLE SPLITTING (limit={max_chars}, debug={debug})")
        print(f"{'=' * 70}")

        for sub in self.subs:
            text = sub.text.strip()
            if not text:
                continue

            wrapper = LineWrapper(text, limit=max_chars, debug=debug)
            wrapper.print()

            print(f"\n[SRT BLOCK {sub.index}]")
            for idx, line in enumerate(wrapper.lines, 1):
                print(f"{idx}: ({len(line)}) {line}")

            # Add colored F1-F3 markers
            if debug:
                for step in ["F1", "F2", "F3"]:
                    self._print_step_log(wrapper, step)

            sub.text = "\n".join(wrapper.lines)

        print(f"\nBrief summary:")
        for sub in self.subs:
            n_lines = len(sub.text.split("\n"))
            print(f"[{sub.index}] {n_lines} lines")

        if log_file:
            sys.stdout = sys.__stdout__
            f.close()

    def _print_step_log(self, wrapper, step):
        """Helper function for colored printing of F1-F3"""
        color = self.COLORS.get(step, "")
        end = self.COLORS["END"]
        lines = getattr(wrapper, f"{step.lower()}_log", None)
        if lines:
            print(f"{color}[{step} LOG]{end}")
            for l in lines:
                print(f"{color}  {l}{end}")

    def save(self, output_path: str):
        self.subs.save(output_path, encoding="utf-8")

    def stats(self):
        total_lines = 0
        total_chars = 0

        for sub in self.subs:
            lines = sub.text.split("\n")
            total_lines += len(lines)
            total_chars += sum(len(l) for l in lines)

        print("\nStatistics:")
        print("-" * 40)
        print(f"Lines: {total_lines}")
        print(f"Characters: {total_chars}")
        if total_lines:
            print(f"Average length: {total_chars / total_lines:.1f}")