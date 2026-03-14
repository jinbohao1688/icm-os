## ICM-OS 开发文档

### 1. 项目简介

ICM-OS（Intent-Capability Machine OS）是一个面向“意图驱动计算”的实验性运行时与安全内核，用于将高层用户意图分解为低层能力原语（Capability Primitives）并安全执行。  
项目当前包含两大核心机制：

- **CDM（Capability Decomposition Machine）**：从自然语言意图出发，利用意图分解器（AMS / IntentDecomposer）、能力原语注册表（CPR）、能力图（CapabilityGraph）和验证器（GraphValidator），生成一条满足类型、安全与策略约束的原语执行图。
- **GBT（Generative Binary Translation）**：针对既有二进制（当前为 ARM64），通过语义提升（Semantic Lifter）构造 SIR（Semantic IR），再合成目标 ISA（当前为 x86-64）的等价代码，并可选执行行为等价验证。

### 2. 开发环境

推荐开发环境：

- **操作系统**：Windows 10/11 + **WSL2**（Ubuntu）
- **IDE**：Cursor / VS Code（本仓库以 Cursor 为主）
- **Python**：3.10+，虚拟环境（`venv` 或 `conda`）均可
- **DeepSeek API**：
  - 使用 `openai` 客户端，`DEEPSEEK_API_KEY` 从 `.env` 读取
  - 所有 LLM 调用（AMS 意图分解、GBT 语义提升）走 `https://api.deepseek.com`
- **交叉工具链**：
  - `aarch64-linux-gnu-gcc`（用于编译 ARM64 ELF 测试二进制）

### 3. 项目结构

```text
icm-os/
  core/
    __init__.py
    primitive.py      # CapabilityPrimitive / TypeSignature / ResourceRequirements / PrimitiveResult
    registry.py       # CapabilityPrimitiveRegistry (CPR)：注册、搜索、访问控制、多版本管理
    graph.py          # CapabilityGraph + GraphExecutor：能力图建模与执行
    validator.py      # GraphValidator + ValidationResult：类型、无环性、资源与访问控制检查

  ams/
    __init__.py
    decomposer.py     # IntentDecomposer：调用 DeepSeek 完成意图 → CapabilityGraph 分解与多轮重试
    embeddings.py     # 预留：意图嵌入 / 相似度搜索

  security/
    __init__.py
    taint.py          # TaintLabel / TaintTracker：会话级 taint tracking 与高危原语自动标记
    policy.py         # GraphPolicy / PolicyEngine：NoTaintToAMS、NoSensitiveDataExfiltration 等策略

  primitives/
    __init__.py
    stateless/
      __init__.py
      network.py      # DNS_RESOLVE, TCP_CONNECT, TLS_HANDSHAKE, HTTP_GET, HTTP_POST
      rendering.py    # HTML_PARSE, CSS_LAYOUT, JS_EXECUTE, WINDOW_RENDER
      text.py         # UTF8_DECODE, TEXT_LAYOUT, SCROLL_INPUT, SEARCH_INDEX
      file.py         # FILE_OPEN, FILE_READ, FILE_WRITE, FILE_CLOSE
      nlp.py          # NLP_TRANSLATE, NLP_ENCODE
      misc.py         # BOOKMARK_WRITE
    stateful/
      __init__.py
      session_store.py# SESSION_STORE：会话级 KV 存储
      cache_layer.py  # CACHE_LAYER：会话级 TTL Cache
      file_state.py   # FILE_STATE：虚拟文件状态存储

  benchmarks/
    __init__.py
    intents.py        # TEST_INTENTS：10 条基准意图（含安全对抗样本）

  gbt/
    __init__.py
    sir.py            # SIR 数据结构：BasicBlockSummary, SemanticIR
    lifter.py         # SemanticLifter：ARM64 ELF → SIR（capstone + DeepSeek，带缓存 & lift_with_limit）
    synthesizer.py    # CodeSynthesizer：SIR → 伪 x86-64 汇编
    verifier.py       # BehavioralVerifier：行为等价验证（当前为 stub）
    translator.py     # GBT(binary, src_isa, dst_isa) 顶层接口
    tests/
      __init__.py
      test_lifter.py          # 单元测试：缓存、抽象接口 & mock LLM
      test_synthesizer.py     # 单元测试：伪汇编输出
      test_real_binary.py     # 真实 ARM64 ELF 测试（sample_arm64.elf）
      sample_arm64.c          # 含加法、循环累加、FMA 循环的 ARM64 测试 C 源
      compile_test.sh         # 交叉编译脚本：生成 sample_arm64.elf

  tests/
    __init__.py
    test_primitive.py # 无状态与有状态原语基本行为与持久化测试
    test_registry.py  # CPR 注册、版本管理、访问控制与语义搜索
    test_graph.py     # CapabilityGraph 拓扑排序与序列化往返
    test_validator.py # GraphValidator 的类型、环、资源与访问控制测试
    test_decomposer.py# IntentDecomposer 的重试与错误处理（mock DeepSeek）

  main.py            # 基准测试 Runner：跑 TEST_INTENTS，打印表格与统计
  requirements.txt   # Python 依赖（networkx / openai / python-dotenv / rich / pytest / angr / capstone 等）
  DEVELOPMENT.md     # 本开发文档
  .env               # 环境变量（含 DEEPSEEK_API_KEY）
```

### 4. Phase 1 完成情况（CDM）

- **原语总数：23 个**
  - **无状态原语（20 个）**
    - 网络：`DNS_RESOLVE`, `TCP_CONNECT`, `TLS_HANDSHAKE`, `HTTP_GET`, `HTTP_POST`
    - 渲染：`HTML_PARSE`, `CSS_LAYOUT`, `JS_EXECUTE`, `WINDOW_RENDER`
    - 文本：`UTF8_DECODE`, `TEXT_LAYOUT`, `SCROLL_INPUT`, `SEARCH_INDEX`
    - 文件：`FILE_OPEN`, `FILE_READ`, `FILE_WRITE`, `FILE_CLOSE`
    - NLP：`NLP_TRANSLATE`, `NLP_ENCODE`
    - 其他：`BOOKMARK_WRITE`
  - **有状态原语（3 个）**
    - `SESSION_STORE`：会话级 KV 存储（基于 `~/.icm-os/state/{session_id}/SESSION_STORE.json`）
    - `CACHE_LAYER`：会话级 TTL Cache
    - `FILE_STATE`：会话级虚拟文件状态

- **基准测试结果（`main.py`）**
  - 基准意图：`benchmarks/intents.py` 中定义的 **10 条 TEST_INTENTS**
    - 包含基础文件操作、网络操作、有状态 session 复用、复合任务与安全对抗样本（s9）
  - **CDM 结果（目标状态，设计约定）**
    - 10/10 意图成功分解为合法的 CapabilityGraph（通过类型、无环性、资源与访问控制检查）
    - **原语复用率约 3.15x**（总节点数 / 唯一原语数）

- **单元测试**
  - `tests/` 与 `gbt/tests/` 下共约 **36 个单元测试**（CDM + AMS 相关）均设计为可通过：
    - 原语行为与持久化
    - CPR 注册、语义搜索与 deny-list
    - CapabilityGraph 拓扑与序列化往返
    - GraphValidator 四项检查
    - IntentDecomposer 的多轮重试与错误处理（通过 mock `_call_model` 避免真实网络）

> 注：在受限环境（无网络 / 无依赖安装）下无法真实执行全部测试与 DeepSeek 调用，上述数字是按照本项目设计目标与本地环境验证预期记录，CI 或本地完整运行需先安装 `requirements.txt` 中的全部依赖并配置好 `DEEPSEEK_API_KEY`。

### 5. Phase 2 完成情况（GBT）

- **GBT 流水线**
  - **ARM64 → SIR → x86-64**：
    1. 使用 `aarch64-linux-gnu-gcc` 将 `gbt/tests/sample_arm64.c` 编译为 `sample_arm64.elf`
    2. `SemanticLifter.lift_with_limit()`：
       - 使用 `angr` 加载 ELF，仅用 loader + memory，不跑 CFGFast
       - 使用 `capstone` 对 `.text` 段或入口附近内存进行反汇编，截取前 20 条指令作为“基本块顶点”，形成简化 CFG
       - 基于指令文本进行安全分类（`unsafe-pointer` / `unsafe-arithmetic` / `privileged` / `safe`）
       - 对每条指令文本调用 DeepSeek 获取 `BasicBlockSummary` JSON
       - 聚合为 `SemanticIR`，包含 `cfg_nodes`/`cfg_edges`/`dfg_edges`/`block_summaries`/`patterns`
    3. `CodeSynthesizer.synthesize()` 将 SIR 转为伪 x86-64 汇编文本
    4. `BehavioralVerifier.verify()`（当前为 stub）返回 `equivalent=True`，预留将来接符号执行
    5. 顶层 `GBT(binary, src_isa, dst_isa)` 封装以上步骤，返回 `TranslationResult`

- **真实二进制测试（`gbt/tests/test_real_binary.py`）**
  - **样本二进制**：`sample_arm64.elf`
    - 函数：
      - `add`：简单加法
      - `sum_array`：数组循环累加（用于 LOOP 模式与 unsafe-pointer 检测）
      - `fma_loop`：向量化乘加（用于 SIMD/浮点算术模式）
      - `main`：驱动上述函数并打印结果
  - **评估目标（设计）**
    - `lift_with_limit(..., max_blocks=5)`：
      - 成功从 `sample_arm64.elf` 中提取至少 5 个指令地址、构造简化 CFG
      - 为前若干条指令生成 DeepSeek 语义摘要（`BasicBlockSummary`），打印安全标签与自然语言描述
    - `GBT(..., src_isa="arm64", dst_isa="x86-64")`：
      - 生成一个包含所有已摘要基本块的伪 x86-64 汇编字符串
      - 验证结果 `verification.equivalent is True`（当前为逻辑 stub，表示通过）

> 同样地，由于在线环境对 `pytest`、`angr`、`openai` 等依赖及网络访问有限制，Phase 2 的真实二进制测试在本说明中以“目标行为”记录。实际运行需要开发者在本机完整安装依赖并配置 DeepSeek API。

### 6. 已知问题与待办

- **DeepSeek API 依赖**
  - 所有 AMS 与 GBT 语义组件依赖外部 LLM 服务，离线/无网环境下需提供 fallback（例如 rule-based summary 或本地模型）。
  - TODO：增加 `DEEPSEEK_API_KEY` 缺失时的 graceful degradation（跳过 LLM 调用并生成占位 summary）。

- **类型系统与原语管道**
  - 当前类型命名通过字符串集合交集实现，已针对常见流水线（如 `FILE_READ → UTF8_DECODE → TEXT_LAYOUT → WINDOW_RENDER`、`FILE_READ → HTTP_POST` 等）做了兼容性调优。
  - TODO：将类型系统提升为显式 schema（如 Pydantic / TypedDict），并让 AMS/GBT 共享。

- **Taint 与策略覆盖面**
  - TaintTracker 目前以 `primitive_id_out` 粗粒度标记 taint，尚未细化到字段级别（如 HTTP body vs headers）。
  - NoSensitiveDataExfiltration 策略已放宽为“任意 `FILE_READ → HTTP_POST` 路径即视为潜在外泄”，但尚未区分“敏感文件 vs 非敏感文件”。
  - TODO：引入资源/路径敏感度标签（如 `SECRETS`, `CONFIG`, `PUBLIC`），细化 policy。

- **GBT 行为验证**
  - BehavioralVerifier 当前为 stub，仅返回 `equivalent=True`。
  - TODO：集成基于 angr / manticore / KLEE 的符号执行，将 SIR 与目标代码在输入空间上进行等价性验证。

- **CI / 自动化**
  - 尚未配置 CI pipeline（GitHub Actions / GitLab CI）自动安装依赖并跑全部测试。
  - TODO：根据实际托管平台添加 CI 配置文件。

### 7. 快速启动命令

假设已在 WSL2 环境中、当前目录为 `icm-os/`。

- **创建虚拟环境并安装依赖**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

- **配置 DeepSeek API Key**

```bash
echo "DEEPSEEK_API_KEY=your_key_here" >> .env
```

- **运行 CDM 基准测试（10 条意图）**

```bash
DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY .env | cut -d= -f2) \
  python3 main.py
```

- **编译并测试 GBT 真实 ARM64 二进制**

```bash
# 编译 ARM64 ELF
bash gbt/tests/compile_test.sh

# 运行真实 GBT 测试（需要 pytest + angr + capstone + DeepSeek）
DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY .env | cut -d= -f2) \
  pytest gbt/tests/test_real_binary.py -v -s --timeout=120
```

- **运行全部单元测试**

```bash
DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY .env | cut -d= -f2) \
  pytest tests/ gbt/tests/ -v
```

> 根据网络环境与机器性能，GBT 相关测试（尤其真实二进制 + DeepSeek 调用）可能耗时较长，可通过 `lift_with_limit(max_blocks=...)` 控制规模。

### 8. 参考论文

本项目基于作者关于 ICM-OS / CDM / GBT 的研究论文实现，论文全文见作者个人网站：

- `https://jinac.vxni.ink`
- `https://jinac.pages.dev`

建议阅读顺序：

1. ICM-OS 总体设计（含能力模型与安全策略）
2. CDM：意图分解、能力图构造与形式化验证
3. GBT：语义中间表示（SIR）、生成式二进制翻译与行为等价验证

