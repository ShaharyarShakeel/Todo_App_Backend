from dataclasses import dataclass


@dataclass(frozen=True)
class TodoDescription:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip())
