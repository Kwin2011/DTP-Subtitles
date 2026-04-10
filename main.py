import os
from srt_processor import SRTProcessor
from srt_splitter import SRTSplitter

MAX_CHARS = 36

ROOT_DIR = r"m:\Jun-Sep-25\Inc\AI-khl2602011-004\Target\mRS"

def process_file(input_path):
    base, ext = os.path.splitext(input_path)

    output_file = base + "_processed.srt"
    output_split_file = base + "_split.srt"

    print("\n" + "=" * 60)
    print(f"Processing: {input_path}")
    print("=" * 60)

    # --- preprocessing ---
    processor = SRTProcessor(input_path)

    print("→ Cleaning...")
    processor.clean_text()

    print("→ Splitting (F1/F2/F3)...")
    processor.split(max_chars=MAX_CHARS, debug=False)

    processor.stats()

    print("→ Saving processed file...")
    processor.save(output_file)

    # --- splitting blocks to maximum 2 lines ---
    print("→ Splitting blocks to max 2 lines...")
    splitter = SRTSplitter(output_file)
    splitter.split_blocks()
    splitter.save(output_split_file)

    print(f"✅ Done: {output_split_file}")


def main():
    for root, dirs, files in os.walk(ROOT_DIR):
        for file in files:
            if file.lower().endswith(".srt"):
                full_path = os.path.join(root, file)
                process_file(full_path)


if __name__ == "__main__":
    main()