# ICM-OS

**Intent-Centric Meta-Operating System** — A research prototype for AI-driven capability decomposition and generative binary translation.

> 论文全文见作者个人网站：[jinac.vxni.ink](https://jinac.vxni.ink) · [jinac.pages.dev](https://jinac.pages.dev)

---

## 概述

ICM-OS 是一个意图驱动的元操作系统研究原型，核心主张是：用户不需要安装任何软件，只需表达意图，系统由 AI 自动将意图分解为原子能力图并执行。

项目包含两大核心机制：

**CDM（能力分解模型）**
从自然语言意图出发，通过意图分解器（AMS）、能力原语注册表（CPR）、能力图（CapabilityGraph）和验证器（GraphValidator），生成一条满足类型、安全与策略约束的原语执行图。任何用户意图都可被动态分解为共享的原子能力原语组合，无需安装任何应用。

**GBT（生成式二进制翻译）**
通过语义提升（Semantic Lifter）将源 ISA 二进制构造为语义中间表示（SIR），再合成目标 ISA 的等价代码。与传统 DBT 不同，GBT 从语义理解而非手写规则出发，可泛化到未见过的 ISA 对，无需逐对工程投入。

---

## 项目结构

```
icm-os/
├── core/
│   ├── primitive.py      # CapabilityPrimitive 基类与数据结构
│   ├── registry.py       # CPR 能力原语注册表
│   ├── graph.py          # CapabilityGraph + GraphExecutor
│   └── validator.py      # GraphValidator（类型、无环性、资源、访问控制）
├── ams/
│   ├── decomposer.py     # IntentDecomposer（意图 → 能力图，多轮重试）
│   └── embeddings.py     # 语义嵌入检索（预留）
├── security/
│   ├── taint.py          # TaintTracker（会话级污点追踪）
│   └── policy.py         # PolicyEngine（信息流安全策略）
├── primitives/
│   ├── stateless/        # 20 个无状态原语
│   └── stateful/         # 3 个有状态原语
├── gbt/
│   ├── sir.py            # SIR 数据结构
│   ├── lifter.py         # SemanticLifter（ARM64 → SIR）
│   ├── synthesizer.py    # CodeSynthesizer（SIR → x86-64）
│   ├── verifier.py       # BehavioralVerifier（行为等价验证）
│   ├── translator.py     # GBT() 顶层接口
│   └── tests/            # GBT 单元测试 + 真实二进制测试
├── benchmarks/
│   └── intents.py        # 10 条基准意图（含安全对抗样本）
├── tests/                # CDM 单元测试（36 个）
└── main.py               # 基准测试 Runner
```

---

## Phase 1：CDM 原型

### 能力原语（共 23 个）

**无状态原语（20 个）：**

| 类别 | 原语 |
|---|---|
| 网络 | `DNS_RESOLVE` `TCP_CONNECT` `TLS_HANDSHAKE` `HTTP_GET` `HTTP_POST` |
| 渲染 | `HTML_PARSE` `CSS_LAYOUT` `JS_EXECUTE` `WINDOW_RENDER` |
| 文本 | `UTF8_DECODE` `TEXT_LAYOUT` `SCROLL_INPUT` `SEARCH_INDEX` |
| 文件 | `FILE_OPEN` `FILE_READ` `FILE_WRITE` `FILE_CLOSE` |
| NLP  | `NLP_TRANSLATE` `NLP_ENCODE` |
| 其他 | `BOOKMARK_WRITE` |

**有状态原语（3 个）：**

| 原语 | 功能 |
|---|---|
| `SESSION_STORE` | 会话级 KV 存储，跨图调用持久化 |
| `CACHE_LAYER` | TTL 内容缓存 |
| `FILE_STATE` | 类型安全文件状态绑定 |

### 基准测试结果

| 意图 | 节点数 | 执行链路 |
|---|---|---|
| 打开文件并搜索 | 7 | FILE_OPEN→FILE_READ→UTF8_DECODE→TEXT_LAYOUT→SEARCH_INDEX→WINDOW_RENDER→SCROLL_INPUT |
| 读取并展示配置 | 4 | FILE_OPEN→FILE_READ→UTF8_DECODE→WINDOW_RENDER |
| 抓取网页标题 | 8 | DNS_RESOLVE→TCP_CONNECT→TLS_HANDSHAKE→HTTP_GET→UTF8_DECODE→HTML_PARSE→CSS_LAYOUT→WINDOW_RENDER |
| 登录并书签 | 12 | DNS_RESOLVE→...→SESSION_STORE→JS_EXECUTE→BOOKMARK_WRITE→...→SCROLL_INPUT |
| 翻译文件为法语 | 5 | FILE_OPEN→FILE_READ→UTF8_DECODE→NLP_TRANSLATE→WINDOW_RENDER |

**汇总：**
- 意图分解成功率：**10/10（100%）**
- 原语复用率：**3.15×**
- 单元测试：**36/36 通过**

### 安全机制

- **TaintTracker**：四级污点标签（CLEAN / USER_INPUT / NETWORK / FILE_UNTRUSTED），跨原语自动传播
- **PolicyEngine**：
  - `NoTaintToAMS`：污点数据不得流入 AMS 意图解析入口
  - `NoSensitiveDataExfiltration`：检测并拦截 `FILE_READ → NLP_ENCODE → HTTP_POST` 外泄模式

---

## Phase 2：GBT 原型

### 流水线

```
ARM64 ELF
    │
    ▼ SemanticLifter（capstone 反汇编 + DeepSeek 语义摘要）
    │
SemanticIR（CFG + DFG + BasicBlockSummary × N）
    │
    ▼ CodeSynthesizer
    │
x86-64 伪汇编
    │
    ▼ BehavioralVerifier（符号执行验证，当前为 stub）
    │
TranslationResult
```

### 真实二进制测试结果

测试样本：`sample_arm64.elf`（含 `add`、`sum_array`、`fma_loop` 函数）

```
提取到 5 个基本块：
  0x400740: [unsafe-pointer] Save frame pointer and link register to stack...
  0x400744: [safe] Loads the base address of a memory region into register x3.
  0x400748: [safe] Set register w2 to the immediate value 3.

合成代码片段：
; Synthesized from sample_arm64.elf (arm64 -> x86-64)
; Block 0x400740 (unsafe-pointer)
; Save the frame pointer and link register onto the stack...
L400740:
    ; ... synthesized instructions ...
```

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
echo "DEEPSEEK_API_KEY=your_key_here" > .env

# 3. 运行 CDM 基准测试
python3 main.py

# 4. 编译并测试 GBT
bash gbt/tests/compile_test.sh
pytest gbt/tests/test_real_binary.py -v -s --timeout=120

# 5. 运行全部单元测试
pytest tests/ gbt/tests/ -v
```

---

## 已知问题与待办

| 优先级 | 问题 | 计划 |
|---|---|---|
| 高 | 所有原语为 mock 实现 | 实现真实 HTTP/文件执行 |
| 高 | GBT 验证器为 stub | 集成 angr 符号执行 |
| 中 | 合成器输出伪代码 | 生成真实可执行 x86-64 汇编 |
| 中 | 无 CI 配置 | 添加 GitHub Actions |
| 低 | embeddings.py 为空 | 实现向量嵌入语义检索 |

---

## 参考论文

本项目基于作者关于 ICM-OS / CDM / GBT 的研究论文实现：

- [jinac.vxni.ink](https://jinac.vxni.ink)
- [jinac.pages.dev](https://jinac.pages.dev)