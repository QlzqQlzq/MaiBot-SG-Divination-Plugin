from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DivinationOutput:
    question: str
    title: str
    trigrams: str
    changing_lines: str
    lines: tuple[str, ...]
    interpretation: str
    disclaimer: str = "仅供整理思路，不替代专业判断。"

    def hexagram_text(self) -> str:
        return "\n".join((self.title, self.trigrams, self.changing_lines, *self.lines))

    def as_text(self) -> str:
        return f"{self.hexagram_text()}\n\n{self.interpretation}\n\n{self.disclaimer}"
