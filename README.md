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

## 当前状态 (v0.1 · M3 进行中 · 2026.03)

| 组件 | 状态 | 说明 |
|------|------|------|
| 内核 | ✅ | Linux 6.1.82 LTS，最小化配置，裸机可启动 |
| ICM Shell | ✅ | 意图驱动 shell，CDM: yes，**23个原语** |
| CDM | ✅ | 意图→Capability Graph，分解成功率 10/10 |
| DNS_RESOLVE | ✅ **真实** | socket.gethostbyname 真实解析 |
| HTTP_GET | ✅ **真实** | requests 真实 HTTP/HTTPS 请求 |
| HTML_PARSE | ✅ **真实** | BeautifulSoup 真实解析，提取标题/文本 |
| FILE_READ | ✅ **真实** | 真实文件 I/O |
| FILE_WRITE | ✅ **真实** | 真实文件写入 |
| NLP_TRANSLATE | ✅ **真实** | DeepSeek API，支持10+语言 |
| 网络 | ✅ | e1000 驱动，完整 TCP/IP 栈 |
| GBT | ✅ | ARM64→x86-64 语义翻译 |
| 安全策略 | ✅ | TaintTracker + PolicyEngine |
| ISO 构建 | ✅ | GRUB2 可启动 ISO |

---

## 真实执行演示

### 网页标题提取

```
icm> fetch https://example.com and show the title
Graph: DNS_RESOLVE -> TCP_CONNECT -> TLS_HANDSHAKE -> HTTP_GET -> HTML_PARSE -> WINDOW_RENDER
[DNS_RESOLVE]   ip='104.18.26.120'  domain='example.com'
[HTTP_GET]      status_code=200
[HTML_PARSE]    title='Example Domain'  ✅
```

### 真实 DNS 解析

```
icm> fetch https://httpbin.org/ip
Graph: DNS_RESOLVE -> TCP_CONNECT -> TLS_HANDSHAKE -> HTTP_GET
[DNS_RESOLVE]   ip='34.235.67.238'        ← 真实 IP，非 mock
[HTTP_GET]      origin='38.150.15.31'     ← 真实公网出口 IP
```

### 多语言翻译

```
icm> translate hello to chinese
[NLP_TRANSLATE] translated='你好'  ✅

icm> translate 今天天气很好 to english
[NLP_TRANSLATE] translated='The weather is nice today.'  ✅
```

### 文件读取

```
icm> read file /etc/resolv.conf
Graph: FILE_OPEN -> FILE_READ -> FILE_CLOSE
[FILE_OPEN]  file_id='fh-d40544f1'
[FILE_READ]  bytes_read=19  content='nameserver 8.8.8.8\n'  ✅
```

---

## 系统架构

```
用户输入自然语言意图
        ↓
   AMS 意图分解器 (DeepSeek API)
   + 参数提取器 (url/domain/target_lang/path)
        ↓
  CDM Capability Graph (networkx DAG)
        ↓
  ┌──────────────────────────────────────┐
  │           原语执行器（23个）            │
  │                                      │
  │  ── 网络 ──────────────────────────  │
  │  DNS_RESOLVE    ← 真实 DNS           │
  │  TCP_CONNECT    ← 连接追踪           │
  │  TLS_HANDSHAKE                       │
  │  HTTP_GET       ← 真实 HTTP/HTTPS    │
  │  HTTP_POST                           │
  │                                      │
  │  ── 渲染 ──────────────────────────  │
  │  HTML_PARSE     ← 真实 BeautifulSoup │
  │  CSS_LAYOUT / JS_EXECUTE             │
  │  WINDOW_RENDER                       │
  │                                      │
  │  ── 文件 ──────────────────────────  │
  │  FILE_OPEN/READ/WRITE/CLOSE ← 真实   │
  │                                      │
  │  ── NLP ───────────────────────────  │
  │  NLP_TRANSLATE  ← 真实 DeepSeek API  │
  │  NLP_ENCODE                          │
  │                                      │
  │  ── 有状态 ────────────────────────  │
  │  SESSION_STORE / CACHE_LAYER         │
  │  FILE_STATE                          │
  └──────────────────────────────────────┘
        ↓
     执行结果输出
```

**底层系统栈：**

```
ICM Shell (Python 3.10) + 23 primitives
        ↓
Linux 6.1.82 内核（最小化）
  BINFMT_ELF + FUTEX + PCI
  e1000 网卡 + TCP/IP 协议栈
        ↓
QEMU x86-64 / 裸机
```

---

## 项目结构

```
icm-os/
├── core/
│   ├── primitive.py      # CapabilityPrimitive 基类
│   ├── registry.py       # CPR 能力原语注册表
│   ├── graph.py          # CapabilityGraph + GraphExecutor
│   └── validator.py      # GraphValidator
├── ams/
│   ├── decomposer.py     # IntentDecomposer（意图 → 能力图）
│   └── embeddings.py     # 语义嵌入检索（预留）
├── security/
│   ├── taint.py          # TaintTracker（四级污点）
│   └── policy.py         # PolicyEngine（信息流安全）
├── primitives/
│   ├── stateless/
│   │   ├── network.py    # DNS/TCP/TLS/HTTP ← 真实
│   │   ├── nlp.py        # NLP_TRANSLATE    ← 真实
│   │   ├── file.py       # FILE_*           ← 真实
│   │   ├── rendering.py  # HTML_PARSE       ← 真实
│   │   ├── text.py       # 文本处理原语
│   │   └── misc.py       # 其他原语
│   └── stateful/
│       ├── cache_layer.py
│       ├── file_state.py
│       └── session_store.py
├── gbt/
│   ├── sir.py            # SIR 数据结构
│   ├── lifter.py         # SemanticLifter（ARM64 → SIR）
│   ├── synthesizer.py    # CodeSynthesizer（SIR → x86-64）
│   ├── verifier.py       # BehavioralVerifier
│   ├── translator.py     # GBT() 顶层接口
│   └── tests/
├── benchmarks/
│   └── intents.py        # 10 条基准意图
├── tests/                # 36 个单元测试
├── iso-build/
│   ├── build.sh          # 完整构建脚本（内核+initramfs+ISO）
│   ├── rebuild_initrd.sh # 重启后快速恢复
│   ├── icm_shell.py      # ICM-OS Shell（含参数提取）
│   └── grub/grub.cfg
├── cli.py                # 开发模式 CLI
└── main.py               # 基准测试 Runner
```

---

## 快速开始

### 配置

```bash
git clone https://github.com/jinbohao1688/icm-os.git
cd icm-os
echo "DEEPSEEK_API_KEY=your_key_here" > .env
```

### 开发模式

```bash
pip install -r requirements.txt
python3 cli.py        # 交互式 CLI
python3 main.py       # 基准测试
pytest tests/ -v      # 36 个单元测试
```

### 构建并启动 ISO

```bash
# 依赖（Ubuntu/Debian）
sudo apt install -y build-essential gcc make xorriso \
    grub-pc-bin grub-common busybox-static \
    libelf-dev libssl-dev bc flex bison qemu-system-x86

# 构建（约 30-60 分钟，主要是内核编译）
chmod +x iso-build/build.sh && ./iso-build/build.sh

# 启动
qemu-system-x86_64 \
  -kernel iso-build/work/iso/boot/vmlinuz \
  -initrd iso-build/work/initrd.img \
  -append "console=ttyS0,115200n8 rdinit=/init" \
  -m 1024M -nographic \
  -netdev user,id=net0 -device e1000,netdev=net0
```

### 重启后恢复

```bash
bash iso-build/rebuild_initrd.sh
```

### 网络配置（进入 shell 后）

```
!ip link set eth0 up
!ip addr add 10.0.2.15/24 dev eth0
!ip route add default via 10.0.2.2
!mkdir -p /etc && echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

---

## CDM 原语列表（23个）

**无状态原语（20个）：**

| 类别 | 原语 | 状态 |
|---|---|---|
| 网络 | `DNS_RESOLVE` `TCP_CONNECT` `TLS_HANDSHAKE` `HTTP_GET` `HTTP_POST` | ✅ 真实 |
| NLP | `NLP_TRANSLATE` `NLP_ENCODE` | ✅ 真实 |
| 文件 | `FILE_OPEN` `FILE_READ` `FILE_WRITE` `FILE_CLOSE` | ✅ 真实 |
| 渲染 | `HTML_PARSE` | ✅ 真实 |
| 渲染 | `CSS_LAYOUT` `JS_EXECUTE` `WINDOW_RENDER` | mock |
| 文本 | `UTF8_DECODE` `TEXT_LAYOUT` `SCROLL_INPUT` `SEARCH_INDEX` | mock |
| 其他 | `BOOKMARK_WRITE` | mock |

**有状态原语（3个）：**

| 原语 | 功能 |
|---|---|
| `SESSION_STORE` | 会话级 KV 存储 |
| `CACHE_LAYER` | TTL 内容缓存 |
| `FILE_STATE` | 文件状态绑定 |

---

## GBT 原型

```
ARM64 ELF
    ↓ SemanticLifter（capstone + DeepSeek 语义摘要）
SemanticIR（CFG + DFG + BasicBlockSummary）
    ↓ CodeSynthesizer
x86-64 汇编
    ↓ BehavioralVerifier（待集成 angr）
TranslationResult
```

---

## 里程碑

| 阶段 | 状态 | 内容 |
|---|---|---|
| M1 | ✅ 完成 | 可启动 ISO + CDM + 网络（2026.03） |
| M2 | ✅ 完成 | 真实 DNS / HTTP / 多语言翻译（2026.03） |
| M3 | 🔄 进行中 | HTML_PARSE + FILE_READ 真实化（2026.03） |
| M4 | 📋 计划中 | 持久化存储 + 更多原语真实化 |
| M5 | 📋 计划中 | C/Rust 核心 + 性能优化 |
| M6 | 📋 计划中 | 稳定发行版 v1.0 |

---

## 技术选型

| 层 | 当前 | 未来 |
|----|------|------|
| 内核 | Linux 6.1.82（最小化） | 自研微内核 |
| 运行时 | Python 3.10 | Rust + PyO3 |
| 原语 | Python（核心已真实化） | C/Rust 原生 |
| 意图分解 | DeepSeek API | 本地小模型 |
| 隔离 | 进程级 | Wasm sandbox |
| 二进制验证 | stub | angr 符号执行 |

---

## 基准测试

- 意图分解成功率：**10/10（100%）**
- 原语复用率：**3.15×**
- 单元测试：**36/36 通过**

---

## 安全机制

- **TaintTracker**：四级污点标签（CLEAN / USER_INPUT / NETWORK / FILE_UNTRUSTED），跨原语自动传播
- **PolicyEngine**：
  - `NoTaintToAMS`：污点数据不得流入意图解析入口
  - `NoSensitiveDataExfiltration`：拦截 `FILE_READ → NLP_ENCODE → HTTP_POST` 外泄模式

---

## 参考论文

- [jinac.vxni.ink](https://jinac.vxni.ink)
- [jinac.pages.dev](https://jinac.pages.dev)

---

## License

MIT License

---

*ICM-OS is a research prototype. Not for production use.*
