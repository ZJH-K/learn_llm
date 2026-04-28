# Day 11 · 类型注解 + Pydantic v2:LLM 消息 Schema

## 🎯 目标

把 typing 模块的现代写法(`list[int]` / `int | None` / `Literal` / `TypedDict` / `Protocol`)和 Pydantic v2 三件套(`BaseModel` / `Field` / `ConfigDict`)+ 校验器(`field_validator` / `model_validator`)落到 OpenAI / Anthropic 消息结构上,产出可直接复用的 `Message` Schema。

需求要点:
- `role`:`Literal["user", "assistant", "system"]`
- `content`:1-4000 字符,自动 strip 首尾空格,不能全是空白
- `metadata`:`dict[str, str]`,默认空字典
- `name`:可选(可不传 / 传 None),长度 1-50
- 跨字段:role=system 不许传 name
- 多余字段一律报错(`extra="forbid"`)

---

## 💭 思考过程

### TypedDict 干不了运行时校验

最初想法是 `TypedDict` —— 它能描述"必须有哪些 key + 每个 key 类型"。但它**只在静态检查阶段有效**,运行时给个 `{"role": "hacker", "content": ""}` 仍然通过。这就是 Pydantic 出场的理由:借用 type hint 语法,**在 `__init__` 时真的去校验**。

### 字段级 vs 模型级约束怎么分

- **能用 `Field(min_length=, ge=, pattern=, ...)` 表达的 → 一律 Field**(声明式,Pydantic Rust 内核跑,快)
- **跨字段才用 `model_validator`**(Python 回调,慢一档,但唯一选择)
- 单字段但要写逻辑(比如"必须含中文")才用 `field_validator`

我作业里的 "content 不能全空白" 一开始用 `field_validator` 写,后来发现 `str_strip_whitespace=True + min_length=1` 已经组合实现了(strip 后空字符串触发 min_length 拦截),validator 形同虚设。**先想 Field 能不能干,再写 validator**。

### name 字段的 Optional 陷阱

`name: str | None` 这种类型只表示"值可以是 None",**不代表可省略**。要让 "不传" 也合法,**必须显式给默认值**:`Field(default=None, ...)` 或 `= None`。这条是 Pydantic 头号坑,后面所有 LLM 配置 / API Schema 都会撞上。

---

## 🛠 最终方案

```python
from pydantic import BaseModel, Field, ConfigDict, model_validator, ValidationError
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
```

测试用 4 条用例覆盖:正常通过 / content 全空白 / system+name / 多余字段。

---

## 🪤 踩坑

1. **`BaseModel` 拼成 `Basemodel`** —— ImportError,IDE 红线一定要扫(同样还有 `Field` 拼成 `Filed`)
2. **`Literal` 误以为来自 `pydantic`** —— 实际在 `typing`,Pydantic 只是借用语法
3. **`name: str | None = Field(...)` 没加 default=None** —— Optional 类型不等于可选字段,**Pydantic 仍当必填**(头号坑,4 个测试用例里 3 个都因这条挂了)
4. **`temperature: float = Field(gt=0.0, lt=2.0)`** —— gt/lt 严格不等会拒 0,但 LLM API 中 `temperature=0` 是合法值(贪心采样)。要用 `ge / le`
5. **`field_validator` 实际不会触发** —— `str_strip_whitespace=True` + `min_length=1` 已经组合实现"不能全空白",strip 后空字符串先被 min_length 拦截,validator 流程根本走不到
6. **pydantic 没装就用** —— stage1-python 共享环境一开始没 pydantic,要 `uv add pydantic`

---

## 🔧 /simplify 改动

1. **`model_config` 移到类顶部** —— 它影响下面所有字段的行为(比如 `str_strip_whitespace=True`),放底部读起来"先看到字段才看到行为修饰",理解顺序反了。社区惯例顶部
2. **`Field(default=None, min_length=1, max_length=50)`** —— default 前置,Pydantic 文档示例 default 都放第一个参数位
3. **函数名 `system_name_must_None` → `system_role_forbids_name`** —— 旧名字混了 None 大写违反 PEP 8 + 中式英语,新名字读起来是规则陈述句
4. **错误消息 `"role=system 时 name 必须为 None"`** —— 旧版"role为system,name不为空"不通顺;错误消息要告诉用户该怎么改
5. **`except Exception` → `except ValidationError`** —— 防止吞掉无关 bug(比如 `model_dumps` 拼写错的 AttributeError 会被静默吞)
6. **循环变量 `name` → `label`(HIGH)** —— 旧版 `for name, build in cases:` 遮蔽了模型字段 `name`,在讲 `name` 字段的文件里特别 confusing
7. **缩进对齐** —— `cases` 列表多缩了一层
8. **删了冗余的 `field_validator content_is_white`** —— Field 约束已覆盖(strip + min_length),validator 形同虚设
