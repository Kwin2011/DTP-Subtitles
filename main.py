from srt_processor import SRTProcessor
#from srt_splitter import SRTSplitter

MAX_CHARS = 50

def main():
    input_file = "test-PT-BR.srt"
    output_file = "output.srt"
    output_split_file = "output_split.srt"  # new file after split

    print("=" * 60)
    print("SRT PROCESSOR")
    print("=" * 60)

    # --- preprocessing ---
    processor = SRTProcessor(input_file)

    print("\n→ Cleaning...")
    processor.clean_text()

    print("\n→ Splitting (F1/F2/F3)...")
    processor.split(max_chars=MAX_CHARS, debug=True, log_file="logs.txt")  # True if logging needed

    processor.stats()

    print("\n→ Saving original processed file...")
    processor.save(output_file)
    print("✅ Done:", output_file)

    # --- splitting blocks to maximum 2 lines ---
    print("\n→ Splitting blocks to max 2 lines...")
    splitter = SRTSplitter(output_file)
    splitter.split_blocks()
    splitter.save(output_split_file)
    print("✅ Done split:", output_split_file)


if __name__ == "__main__":
    main()