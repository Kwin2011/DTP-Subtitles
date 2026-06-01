import pysrt


class SRTSplitter:
    """
    Розбиває блоки SRT на підблоки по максимум 2 рядки,
    з пропорційним розподілом таймкодів за вагою символів.
    """

    def __init__(self, input_file):
        self.input_file = input_file
        self.subs = pysrt.open(input_file, encoding='utf-8')

    @staticmethod
    def _calculate_weight(lines):
        return sum(len(line) for line in lines)

    @staticmethod
    def _split_block_lines(lines):
        n = len(lines)
        if n <= 2:
            return [lines]

        if n == 3:
            option1 = [lines[:2], lines[2:]]
            option2 = [lines[:1], lines[1:]]
            imbalance1 = abs(sum(len(l) for l in option1[0]) - sum(len(l) for l in option1[1]))
            imbalance2 = abs(sum(len(l) for l in option2[0]) - sum(len(l) for l in option2[1]))
            return option1 if imbalance1 <= imbalance2 else option2

        if n == 4:
            return [lines[:2], lines[2:]]

        if n == 5:
            options = [
                [lines[:2], lines[2:4], lines[4:]],
                [lines[:1], lines[1:3], lines[3:]],
            ]
            def imbalance(opt):
                ws = [sum(len(l) for l in blk) for blk in opt]
                return max(ws) - min(ws)
            return min(options, key=imbalance)

        result = []
        i = 0
        while i < n:
            result.append(lines[i:i + 2])
            i += 2
        return result

    @staticmethod
    def _seconds_to_srttime(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return pysrt.SubRipTime(hours=hours, minutes=minutes, seconds=secs,
                                milliseconds=milliseconds)

    def split_blocks(self, report=None, logger=None):
        new_subs = []
        blocks_split = 0

        for sub in self.subs:
            lines = sub.text.split("\n")
            total_weight = self._calculate_weight(lines)

            if total_weight == 0:
                if logger:
                    logger.console_warn(f"block #{sub.index} is empty — skipped")
                continue

            split_lines = self._split_block_lines(lines)

            if len(split_lines) > 1:
                blocks_split += len(split_lines) - 1
                if report:
                    report.add_blocks_split(len(split_lines) - 1)
                if logger:
                    logger.log_block_split(sub.index, split_lines)

            start_s = (sub.start.hours * 3600 + sub.start.minutes * 60
                       + sub.start.seconds + sub.start.milliseconds / 1000)
            end_s   = (sub.end.hours * 3600 + sub.end.minutes * 60
                       + sub.end.seconds + sub.end.milliseconds / 1000)
            total_s = end_s - start_s
            accumulated = 0

            for blk in split_lines:
                blk_weight = self._calculate_weight(blk)
                blk_s = (total_s * (blk_weight / total_weight)
                         if blk_weight and total_weight
                         else total_s / len(split_lines))

                new_subs.append(pysrt.SubRipItem(
                    index=len(new_subs) + 1,
                    start=self._seconds_to_srttime(start_s + accumulated),
                    end=self._seconds_to_srttime(start_s + accumulated + blk_s),
                    text="\n".join(blk)
                ))
                accumulated += blk_s

        self.subs = pysrt.SubRipFile(new_subs)
        return blocks_split

    def save(self, output_file):
        self.subs.save(output_file, encoding='utf-8')
