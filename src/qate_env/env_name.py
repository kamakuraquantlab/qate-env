import re
from typing import Self

_PATTERN = re.compile(r"^[A-Z_]+$")


class EnvName(str):
    def __new__(cls, value: str) -> Self:
        if not _PATTERN.fullmatch(value):
            raise ValueError(f"Invalid EnvName {value!r}: must match [A-Z_]+")
        return super().__new__(cls, value)
