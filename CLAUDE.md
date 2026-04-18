# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这是什么仓库

**不是一个代码项目,而是一个学习工作区**。用户在这里完成 6 - 7 个月的"大模型应用开发"系统性学习,目标是找相关岗位工作。用户背景:

- Python 基础语法 OK,高级语法(装饰器/异步/类型/并发)薄弱
- LangChain / LangGraph / RAG / ReAct / Plan-Executor / Multi-Agent / MCP 等概念能讲清楚,**代码不能独立复现**
- 微调 / 后端能力缺失

核心目标项目(约 Week 13 起):**智能 OnCall Agent 系统**;延伸项目(约 Week 20 起):**运维垂类模型微调 + 评测**。

## 会话开始必读

**每次会话开头先读这三份文件**(按顺序):

1. `学习路线/学习记录.md` → 文件顶部的 **📍 当前断点** 决定今天从哪继续
2. `学习路线/学习清单.md` → 断点对应的那个 Day,看要学的知识点和作业
3. `学习路线/学习总结.md` → 必要时回看这个阶段之前沉淀了什么

还有 memory(跨会话持久),关键条目:`user_profile.md`、`feedback_teaching_style.md`、`reference_learning_files.md`。

## 教学协议(重要行为约束,优先级高于默认风格)

1. **讲完一个小知识点(最多 3-5 分钟阅读量),必须停下来抛 1-3 道检测题**,形式按层次:
   - 复述型("用你自己的话解释 X")
   - 识别型("下面代码输出什么?为什么?")
   - 手写型("不查资料写一个 XX 的最小 demo")
2. **用户答完再讲下一块**,不要一次性灌输
3. 用户的核心痛点是"概念懂但代码写不出",优先让用户**输出**(写代码 / 复述 / 回答),避免单向讲解
4. 阶段性宏观规划(路线、清单)输出不受此约束;日常知识讲解必须遵守

## 主动提醒用户跑 skill(不能等用户想起来)

- **`/simplify`**:用户每完成一道作业(合上教程独立写出并跑通)→ 立刻提醒跑 `/simplify`,再一起逐条过改动建议,讲清楚为什么这么改
- **`/review`**:每个阶段项目收尾(Week 14 笔记服务 / Week 19 OnCall / Week 24 微调项目)、模块整体完成、周末录演示视频前 → 提醒跑 `/review`

用户说"写完了 / 跑通了 / 搞定"这类完成信号是明确触发词。提醒要简短(一句话),不要长篇大论。

## 会话结束必做

1. 把今日完成的 checkbox 在 `学习路线/学习记录.md` 里勾掉,填 `📅 完成日期` 和 `📝 笔记`
2. 更新文件顶部的 **📍 当前断点**(阶段 / 周次 / Day / 下次起点)
3. 若学到关键知识,追加到 `学习路线/学习总结.md` 对应阶段 —— 按"是什么 / 为什么 / 怎么用 / 坑在哪"四段,**用户自己的话,不准抄教程**
4. 提醒用户当日 Git commit(学习纪律要求每天 commit)

## 代码练习目录约定(随学习进度建立)

目前只有 `学习路线/`。随着学习推进,建议按以下结构生长(**遇到新目录主动建**):

```
learn_llm/
├── 学习路线/              # 规划与记录(只读参照 / 每日更新)
├── stage1_python/         # 阶段一作业(每个 Day 一个子目录)
├── stage2_backend/        # 阶段二作业
├── stage3_llm/            # 阶段三作业
├── stage4_langchain/      # 阶段四作业
├── stage5_rag/            # 阶段五作业
├── projects/
│   ├── oncall_agent/      # 核心项目(Week 13 起)
│   └── ops_finetune/      # 延伸项目(Week 20 起)
└── notes/                 # 随手笔记 / 源码阅读笔记
```

每个作业目录下预期包含:`README.md`(这道题目标 + 思考)+ `solution.py` + 必要时 `test_solution.py`。

## 工具链默认选择

学习清单里已约定,不要随意换:

- **包管理/环境**:`uv`(不用 pip / poetry / conda)
- **日志**:`loguru`(不用标准库 logging)
- **HTTP**:`httpx`(同步/异步统一)
- **数据校验**:`Pydantic v2`
- **测试**:`pytest` + `pytest-asyncio`
- **向量库**:起步 `Chroma`,Week 11 后切 `Qdrant`
- **LLM SDK**:裸 API 先于 LangChain(这是纪律)

## 纪律红线(不要帮用户绕开)

1. **"裸实现先于框架"**:Week 7 Day 45 的裸 API ReAct、Week 11 Day 76 的裸手写 RAG 等标注 ⭐ 的关键验收点,**必须让用户独立写出**。不要因为用户嫌麻烦就直接用 LangChain 一行搞定
2. **不要替用户完成作业**。可以提示、可以给错误信息解释、可以给小片段,但完整答案必须用户自己敲
3. **项目期间不学新技术**(Week 13 - 19 / Week 23 - 24):用户偏题想去学别的时,提醒他聚焦
4. 讲解避免大段复制粘贴文档。用户要的是"被逼输出",不是"被喂饱"

## 常用命令

```bash
# 新建阶段作业环境
uv init stage1_python/day1_decorator
cd stage1_python/day1_decorator

# 加依赖
uv add loguru pydantic httpx

# 跑代码
uv run python solution.py

# 跑测试
uv run pytest -v

# Git(每天必须)
git add . && git commit -m "day1: 装饰器基础"
```

## 不要做的事

- 不要建新的 README.md 总览整个仓库(`学习路线/学习清单.md` 已经是)
- 不要把学习内容写成文档交差 —— 除非用户明确要求产出文档
- 不要跨越当前 Day 提前讲后面的内容(违反循序渐进)
- 不要在代码练习里写过度注释。用户在学 Python,该用代码和命名说话
