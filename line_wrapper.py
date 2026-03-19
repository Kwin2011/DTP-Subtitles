import math
import re


class LineWrapper:
    PUNCT = {",", ";", ":", ".", "!", "?", ")"}

    def __init__(self, text, limit=50, debug=False):
        self.text = text.strip()
        self.limit = limit
        self.debug = debug

        self.lines = []
        self.N = 0
        self.avg = 0

        self._process()

    # ---------------- LOG ----------------
    def _log(self, msg):
        if self.debug:
            print(msg)

    # ---------------- HELPERS ----------------
    def _words(self, line):
        return line.split()

    def _join(self, words):
        return " ".join(words)

    def _ends_with_punct(self, word):
        return len(word) > 0 and word[-1] in self.PUNCT

    # ---------------- STEP 1: GREEDY ----------------
    def _greedy_split(self):
        self._log("\n[STEP 1] GREEDY SPLIT")

        words = self.text.split()
        cur = ""

        for w in words:
            candidate = (cur + " " + w).strip()

            #self._log(f" try add '{w}' → '{candidate}' ({len(candidate)})")

            if len(candidate) <= self.limit:
                cur = candidate
            else:
                #self._log(f"  -> push line: '{cur}'")
                self.lines.append(cur)
                cur = w

        if cur:
            self._log(f"  -> final push: '{cur}'")
            self.lines.append(cur)
    # ---------------- F1 ----------------
    def _F1(self, i):
        self._log(f"\n[F1] Processing line {i} (technical and semantic transfer)")

        words_i = self._words(self.lines[i])
        words_next = self._words(self.lines[i + 1])

        # --- Stage 1: technical ---
        moved = False
        while len(self._join(words_i)) > self.limit:
            last = words_i.pop()
            words_next.insert(0, last)
            moved = True
            self._log(f"  F1-S1: moved '{last}' → next line (len now {len(self._join(words_i))})")
        if not moved:
            self._log("  F1-S1: no movement, length is normal")

        # --- Stage 2: semantic ---
        if len(words_i) >= 3:
            w, w1, w2 = words_i[-1], words_i[-2], words_i[-3]

            if len(w) == 1:
                words_i.pop()
                words_next.insert(0, w)
                self._log(f"  F1-S2: single character '{w}' → next line")
            elif self._ends_with_punct(w1):
                if self._ends_with_punct(w2):
                    self._log(f"  F1-S2: enumeration ({w2}, {w1}, {w}) → skip")
                else:
                    words_i.pop()
                    words_next.insert(0, w)
                    self._log(f"  F1-S2: punctuation rule → moved '{w}'")

        self.lines[i] = self._join(words_i)
        self.lines[i + 1] = self._join(words_next)
        self._log(f"  After F1: [{i}]='{self.lines[i]}' | [{i+1}]='{self.lines[i+1]}'")


    # ---------------- F2 ----------------
    def _F2(self, i):
        self._log(f"\n[F2] Processing line {i} (pulling from next line)")

        words_i = self._words(self.lines[i])
        words_next = self._words(self.lines[i + 1])
        if not words_next:
            self._log("  F2: next line empty → skip")
            return

        first = words_next[0]
        lastI = words_i[-1] if words_i else ""

        # -----------------------
        # Protection against F1
        # -----------------------
        if len(first) == 1:
            self._log(f"  F2: first word '{first}' = 1 character → skip")
            return
        if self._ends_with_punct(lastI):
            self._log(f"  F2: last word '{lastI}' ends with punctuation → skip")
            return

        # -----------------------
        # Main condition: move word only when justified
        # -----------------------
        space = self.limit - len(self.lines[i])
        if (self._has_punct_after(first) or self._has_comma_dash_before(words_next)) and len(first) <= space:
            words_next.pop(0)
            words_i.append(first)
            self._log(f"  F2: pulled '{first}' → current line (len now {len(self._join(words_i))})")
        else:
            self._log(f"  F2: '{first}' doesn't meet transfer conditions → skip")

        # -----------------------
        # Contextual pulling of sentence end
        # -----------------------
        if words_i and self._ends_with_punct(first):
            prevLast = words_i[-1]
            if not self._ends_with_punct(prevLast) and len(prevLast) <= 4:
                words_i.pop()
                words_next.insert(0, prevLast)
                self._log(f"  F2: contextual pulling '{prevLast}' → next line")

        # -----------------------
        # Apply changes
        # -----------------------
        self.lines[i] = self._join(words_i)
        self.lines[i + 1] = self._join(words_next)
        self._log(f"  After F2: [{i}]='{self.lines[i]}' | [{i+1}]='{self.lines[i+1]}'")


    # Example helper functions
    def _has_punct_after(self, word):
        # Returns True if word is followed by end of sentence
        return word[-1] in ".!?;"

    def _has_comma_dash_before(self, words):
        # Checks if word is preceded by ',' or '-'
        # Only considers the first word
        return len(words) > 1 and words[0].startswith((',', '-'))


    # ---------------- F3 ----------------
    def _F3(self, i, avg=None):
        """Move last word of current line to next line considering context"""
        if i >= len(self.lines) - 1:
            return  # need next line

        words_i = self._words(self.lines[i])
        words_next = self._words(self.lines[i + 1])
        if not words_i:
            return

        last = words_i[-1]
        len_last = len(last)

        # 1. Punctuation check: don't move if word ends with punctuation and next line logically continues the thought
        if self._ends_with_punct(last):
            # check beginning of next line
            first_next = words_next[0] if words_next else ""
            if first_next and first_next[0].islower():
                self._log(f"F3: '{last}' ends with punctuation, next line continues → skip")
                return
            # otherwise can move if it fits
            if len(self._join(words_next)) + len_last + 1 <= self.limit:
                words_i.pop()
                words_next.insert(0, last)
                self._log(f"F3: moved '{last}' due to punctuation and length")
                self.lines[i] = self._join(words_i)
                self.lines[i + 1] = self._join(words_next)
                return

        # 2. If word without punctuation, try based on length difference
        diff_len = len(self.lines[i]) - len(self.lines[i + 1])
        if diff_len > 1.5 * len_last:
            if len(self._join(words_next)) + len_last + 1 <= self.limit:
                words_i.pop()
                words_next.insert(0, last)
                self._log(f"F3: moved '{last}' due to large length difference ({diff_len})")
                self.lines[i] = self._join(words_i)
                self.lines[i + 1] = self._join(words_next)
                return

        self._log(f"F3: '{last}' not eligible for transfer")

    # ---------------- MAIN ----------------
    def _process(self):
        # ---------------- STEP 1: GREEDY ----------------
        self._greedy_split()

        # ---------------- INIT ----------------
        total_len = len(self.text)
        self.N = math.ceil(total_len / self.limit)
        self.avg = total_len / self.N if self.N else 0

        self._log(f"\n[INIT] N={self.N}, avg={self.avg:.2f}")
        self._log(f"[INIT LINES] {self.lines}")

        # ensure there is a next line
        if len(self.lines) < self.N:
            self.lines += [""] * (self.N - len(self.lines))

        # ---------------- STEP 1.5: BALANCE BY AVG ----------------
        self._log("\n[STEP 1.5] BALANCE LINES BY AVG")
        for i in range(len(self.lines) - 1):
            while len(self.lines[i]) > self.avg:
                words_i = self._words(self.lines[i])
                words_next = self._words(self.lines[i + 1])

                if not words_i:
                    break

                last = words_i.pop()
                words_next.insert(0, last)

                self.lines[i] = self._join(words_i)
                self.lines[i + 1] = self._join(words_next)

                self._log(f"  [BALANCE] move '{last}' → next (len now {len(self.lines[i])} / avg {self.avg:.2f})")

        self._log(f"[AFTER BALANCE] {self.lines}")

        # ---------------- STEP 2: APPLY F1, F2, F3 ----------------
        for i in range(len(self.lines) - 1):
            self._log(f"\n=== ITER {i} ===")
            self._F1(i)
            self._F2(i)
            self._F3(i)

        # remove empty lines
        self.lines = [l for l in self.lines if l.strip()]

        self._log(f"\n[FINAL] {self.lines}")
    # ---------------- OUTPUT ----------------
    def __str__(self):
        return "\n".join(self.lines)

    def print(self):
        for i, line in enumerate(self.lines, 1):
            print(f"{i}: ({len(line)}) {line}")