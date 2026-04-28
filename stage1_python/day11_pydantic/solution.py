from pydantic import BaseModel, Field, model_validator, ConfigDict, ValidationError
from typing import Literal


class Message(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=4000)
    metadata: dict[str, str] = Field(default_factory=dict)
    name: str | None = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def system_role_forbids_name(self):
        if self.role == "system" and self.name is not None:
            raise ValueError("role=system 时 name 必须为 None")
        return self


if __name__ == "__main__":
    cases = [
        ("用例1", lambda: Message(role="user", content="  hello  ", metadata={"k": "v"})),
        ("用例2", lambda: Message(role="assistant", content="   \n\t  ")),
        ("用例3", lambda: Message(role="system", content="you are helpful", name="oncall_bot")),
        ("用例4", lambda: Message(role="user", content="hi", extra_field="hack")),
    ]

    for label, build in cases:
        try:
            m = build()
            print(f"{label} ✅ 通过 → {m.model_dump()}")
        except ValidationError as e:
            print(f"{label} ❌ {type(e).__name__}: {e}")
