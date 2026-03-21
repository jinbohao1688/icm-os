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

## 当前状态 (v0.1 · M1 完成 · 2026.03)

| 组件 | 状态 | 说明 |
|------|------|------|
| 内核 | ✅ | Linux 6.1.82 LTS，最小化配置，裸机可启动 |
| ICM Shell | ✅ | 意图驱动 shell，CDM: yes，19个原语 |
| CDM | ✅ | 意图→Capability Graph，分解成功率 10/10 |
| 网络 | ✅ | e1000 驱动，DNS/TCP/TLS/HTTP 完整执行链 |
| GBT | ✅ | ARM64→x86-64 语义翻译，真实 ELF 测试通过 |
| 安全策略 | ✅ | TaintTracker + PolicyEngine |
| ISO 构建 | ✅ | GRUB2 可启动 ISO，QEMU 验证通过 |
| GitHub | ✅ | 代码公开发布 |

---

## 系统架构

```
用户输入自然语言意图
        ↓
   AMS 意图分解器 (DeepSeek API)
        ↓
  CDM Capability Graph (networkx DAG)
        ↓
  ┌─────────────────────────────┐
  │      原语执行器（19个）       │
  │  DNS_RESOLVE → TCP_CONNECT  │
  │  → TLS_HANDSHAKE → HTTP_GET │
  │  NLP_TRANSLATE / FILE_READ  │
  │  SESSION_STORE / CACHE ...  │
  └─────────────────────────────┘
        ↓
     执行结果输出
```

**底层系统栈：**
```
ICM Shell (Python 3.10)
        ↓
Linux 6.1.82 内核（最小化）
  CONFIG_BINFMT_ELF + FUTEX
  e1000 网卡 + PCI
        ↓
QEMU x86-64 / 裸机
```

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
├── iso-build/            # ISO 构建系统
│   ├── build.sh          # 完整构建脚本（内核+initramfs+ISO）
│   ├── rebuild_initrd.sh # 重启后快速恢复脚本
│   ├── icm_shell.py      # ICM-OS Shell 主程序
│   └── grub/grub.cfg     # GRUB2 启动配置
├── cli.py                # 开发模式交互 CLI
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
  0x400740: [unsafe-pointer] Save frame pointer and link register to stack
  0x400744: [safe] Loads the base address of a memory region into register x3
  0x400748: [safe] Set register w2 to the immediate value 3

合成代码片段：
; Synthesized from sample_arm64.elf (arm64 -> x86-64)
; Block 0x400740 (unsafe-pointer)
L400740:
    ; ... synthesized instructions ...
```

---

## Phase 3：ISO 构建（M1 完成）

### 内核配置（Linux 6.1.82）

```
CONFIG_BINFMT_ELF=y       # ELF 可执行文件支持
CONFIG_BINFMT_SCRIPT=y    # shell 脚本支持
CONFIG_FUTEX=y            # Python 线程支持
CONFIG_NET=y              # 网络支持
CONFIG_E1000=y            # Intel e1000 网卡
CONFIG_PCI=y              # PCI 总线
CONFIG_INET=y             # TCP/IP 协议栈
```

### 真实执行链（内核上验证）

```
icm> fetch the webpage at http://example.com
[AMS] Graph: DNS_RESOLVE → TCP_CONNECT → TLS_HANDSHAKE → HTTP_GET
[DNS_RESOLVE] ip: 93.184.216.34  ttl: 300
[TCP_CONNECT] status: CONNECTED
[TLS_HANDSHAKE] cert_valid: True
[HTTP_GET] status_code: 200
Result: <!doctype html><html...
```

---

## 快速开始

### 开发模式（不需要 ISO）

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

# 5. 交互式 CLI
python3 cli.py
```

### 构建并启动 ISO

```bash
# 安装系统依赖
sudo apt install -y build-essential gcc make xorriso \
    grub-pc-bin grub-common busybox-static \
    libelf-dev libssl-dev bc flex bison qemu-system-x86

# 构建（约 30-60 分钟，主要是编译内核）
chmod +x iso-build/build.sh
./iso-build/build.sh

# 启动
qemu-system-x86_64 \
  -kernel iso-build/work/iso/boot/vmlinuz \
  -initrd iso-build/work/initrd.img \
  -append "console=ttyS0,115200n8 rdinit=/init" \
  -m 1024M -nographic \
  -netdev user,id=net0 \
  -device e1000,netdev=net0
```

### 重启后快速恢复

```bash
~/icm-os/iso-build/rebuild_initrd.sh
```

---

## 使用示例

### 开发模式 CLI

```
Read /tmp/notes.txt and display its contents
✓ Graph: FILE_OPEN → FILE_READ → UTF8_DECODE → WINDOW_RENDER
✓ FILE_READ     → bytes_read: 58
✓ UTF8_DECODE   → text: 'Hello world...'

Fetch the webpage at https://example.com and show its title
✓ Graph: DNS_RESOLVE → TCP_CONNECT → TLS_HANDSHAKE → HTTP_GET → HTML_PARSE
✓ HTTP_GET      → status_code: 200
✓ HTML_PARSE    → title: 'Example Domain'
```

### ICM-OS Shell（内核上）

```
# 自然语言意图
icm> translate hello to chinese
icm> fetch the webpage at http://example.com
icm> read file /icm-os/icm_shell.py

# 传统命令（加 ! 前缀）
icm> !ls /
icm> !ip link set eth0 up
icm> !cat /etc/resolv.conf
```

---

## 里程碑

| 阶段 | 状态 | 内容 |
|---|---|---|
| M1 | ✅ 完成 | 可启动 ISO + CDM + 网络（2026.03） |
| M2 | 🔄 进行中 | 修复翻译 / 完善原语 / DNS 稳定性 |
| M3 | 📋 计划中 | 包管理器 + 持久化存储 |
| M4 | 📋 计划中 | C/Rust 核心原语 + 性能优化 |
| M5 | 📋 计划中 | 稳定发行版 v1.0 |

---

## 技术选型

| 层 | 当前 | 未来规划 |
|----|------|------|
| 内核 | Linux 6.1.82（最小化） | 自研微内核 |
| 运行时 | Python 3.10 | Rust + PyO3 |
| 原语实现 | Python（部分 mock） | C/Rust 原生实现 |
| 意图分解 | DeepSeek API | 本地小模型 |
| 安全隔离 | 进程级 | Wasm sandbox |
| 二进制翻译验证 | stub | angr 符号执行 |

---

## 已知问题与待办

| 优先级 | 问题 | 计划 |
|---|---|---|
| 高 | 部分原语为 mock 实现 | 实现真实 HTTP/文件执行 |
| 高 | GBT 验证器为 stub | 集成 angr 符号执行 |
| 中 | 合成器输出伪代码 | 生成真实可执行 x86-64 汇编 |
| 中 | 无 CI 配置 | 添加 GitHub Actions |
| 低 | embeddings.py 为空 | 实现向量嵌入语义检索 |

---

## 参考论文

本项目基于作者关于 ICM-OS / CDM / GBT 的研究论文实现：

- [jinac.vxni.ink](https://jinac.vxni.ink)
- [jinac.pages.dev](https://jinac.pages.dev)

---

## License

MIT License

---

*ICM-OS is a research prototype. Not for production use.*
