import pysrt

class SRTSplitter:
    """
    Розбиває блоки SRT на підблоки по максимум 2 рядки,
    з пропорційним розподілом таймкодів за вагою символів.
    Для блоків з 3-5 рядків обирає оптимальний поділ з мінімальною різницею ваг.
    """

    def __init__(self, input_file):
        self.input_file = input_file
        self.subs = pysrt.open(input_file, encoding='utf-8')

    @staticmethod
    def _calculate_weight(lines):
        """Сума символів рядків"""
        return sum(len(line) for line in lines)

    @staticmethod
    def _split_block_lines(lines):
        n = len(lines)
        if n <= 2:
            return [lines]

        # Для 3 рядків – обираємо мінімальний дисбаланс
        if n == 3:
            w = [len(l) for l in lines]
            # Варіанти розподілу
            option1 = [lines[:2], lines[2:]]
            option2 = [lines[:1], lines[1:]]
            # Обчислюємо дисбаланс
            imbalance1 = abs(sum(len(l) for l in option1[0]) - sum(len(l) for l in option1[1]))
            imbalance2 = abs(sum(len(l) for l in option2[0]) - sum(len(l) for l in option2[1]))
            return option1 if imbalance1 <= imbalance2 else option2

        # Для 4 рядків – пробуємо два варіанти 2+2
        if n == 4:
            return [lines[:2], lines[2:]]

        # Для 5 рядків – шукаємо мінімальний дисбаланс серед 3 варіантів
        if n == 5:
            options = [
                [lines[:2], lines[2:4], lines[4:]],  # 2+2+1
                [lines[:1], lines[1:3], lines[3:]],  # 1+2+2
            ]
            # Дисбаланс: max(sum_weights) - min(sum_weights)
            def imbalance(opt):
                ws = [sum(len(l) for l in blk) for blk in opt]
                return max(ws) - min(ws)
            return min(options, key=imbalance)

        # Для >5 рядків – розбиваємо по 2 рядки
        result = []
        i = 0
        while i < n:
            result.append(lines[i:i+2])
            i += 2
        return result

    @staticmethod
    def _seconds_to_srttime(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return pysrt.SubRipTime(hours=hours, minutes=minutes, seconds=secs, milliseconds=milliseconds)

    def split_blocks(self):
        """Проходить по блоках і розбиває їх на підблоки по максимум 2 рядки"""
        new_subs = []

        for sub in self.subs:
            lines = sub.text.split("\n")
            split_lines = self._split_block_lines(lines)
            total_weight = self._calculate_weight(lines)

            # обчислюємо час у секундах
            start_seconds = sub.start.hours*3600 + sub.start.minutes*60 + sub.start.seconds + sub.start.milliseconds/1000
            end_seconds = sub.end.hours*3600 + sub.end.minutes*60 + sub.end.seconds + sub.end.milliseconds/1000
            total_seconds = end_seconds - start_seconds

            accumulated_seconds = 0

            for blk in split_lines:
                blk_weight = self._calculate_weight(blk)
                blk_seconds = total_seconds * (blk_weight / total_weight)

                blk_start_seconds = start_seconds + accumulated_seconds
                blk_end_seconds = blk_start_seconds + blk_seconds

                blk_start = self._seconds_to_srttime(blk_start_seconds)
                blk_end = self._seconds_to_srttime(blk_end_seconds)

                new_subs.append(pysrt.SubRipItem(
                    index=len(new_subs)+1,
                    start=blk_start,
                    end=blk_end,
                    text="\n".join(blk)
                ))

                accumulated_seconds += blk_seconds

        # конвертуємо список у SubRipFile
        self.subs = pysrt.SubRipFile(new_subs)

    def save(self, output_file):
        self.subs.save(output_file, encoding='utf-8')
        print("✅ Saved:", output_file)