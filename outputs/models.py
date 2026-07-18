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
        parts = (self.title, self.trigrams, self.changing_lines, *self.lines)
        return "\n".join(parts)

    def as_text(self) -> str:
        content = f"{self.hexagram_text()}\n\n{self.interpretation}\n\n{self.disclaimer}"
        return content
