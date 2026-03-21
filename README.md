# ICM-OS

**Intent-Centric Meta-Operating System** — A research prototype for AI-driven capability decomposition and generative binary translation.

> 论文全文见作者个人网站：[jinac.vxni.ink](https://jinac.vxni.ink) · [jinac.pages.dev](https://jinac.pages.dev)

---

## 概述

ICM-OS 是一个意图驱动的元操作系统研究原型，核心主张是：用户不需要安装任何软件，只需表达意图，系统由 AI 自动将意图分解为原子能力图并执行。

支持任意语言输入意图——中文、英文、德文、日文……AI 直接理解并执行，零配置。

项目包含两大核心机制：

**CDM（能力分解模型）**
从自然语言意图出发，通过意图分解器（AMS）、能力原语注册表（CPR）、能力图（CapabilityGraph）和验证器（GraphValidator），生成一条满足类型、安全与策略约束的原语执行图。

**GBT（生成式二进制翻译）**
通过语义提升（Semantic Lifter）将源 ISA 二进制构造为语义中间表示（SIR），再合成目标 ISA 的等价代码。与传统 DBT 不同，GBT 从语义理解而非手写规则出发，可泛化到未见过的 ISA 对。

---

## 当前状态 (v0.1 · M3 完成 · 2026.03)

| 组件 | 状态 | 说明 |
|------|------|------|
| 内核 | ✅ | Linux 6.1.82 LTS，最小化配置，裸机可启动 |
| ICM Shell | ✅ | 意图驱动 shell，CDM: yes，**24个原语** |
| 自动网络 | ✅ | 启动时自动配置 eth0，无需手动操作 |
| /data 存储 | ✅ | tmpfs 持久化目录，自动创建 |
| 多语言意图 | ✅ | AMS 直接提取参数，支持任意语言 |
| DNS_RESOLVE | ✅ **真实** | socket.gethostbyname 真实解析 |
| HTTP_GET | ✅ **真实** | requests 真实 HTTP/HTTPS |
| HTML_PARSE | ✅ **真实** | BeautifulSoup 解析标题/文本 |
| FILE_READ | ✅ **真实** | 真实文件读取 |
| FILE_WRITE | ✅ **真实** | 真实文件写入，自动创建目录 |
| NLP_TRANSLATE | ✅ **真实** | DeepSeek API，任意语言互译 |
| NLP_SUMMARIZE | ✅ **真实** | DeepSeek API，网页/文件内容总结 |
| GBT | ✅ | ARM64→x86-64 语义翻译 |
| 安全策略 | ✅ | TaintTracker + PolicyEngine |
| ISO 构建 | ✅ | GRUB2 可启动 ISO |

---

## 真实执行演示

### 任意语言写入文件

```
# 中文
icm> 把"你好世界"写入文件 /data/notes/chinese.txt
Graph: FILE_OPEN -> FILE_WRITE -> FILE_CLOSE
FILE_WRITE: bytes_written=12  ✅
$ cat /data/notes/chinese.txt → 你好世界

# 德文
icm> Schreibe "Hallo Welt" in die Datei /data/notes/german.txt
Graph: FILE_OPEN -> FILE_WRITE -> FILE_CLOSE
FILE_WRITE: bytes_written=10  ✅
$ cat /data/notes/german.txt → Hallo Welt

# 英文
icm> write "hello from ICM-OS" to file /data/notes/test.txt
FILE_WRITE: bytes_written=17  ✅
```

### 网页抓取 + AI 总结

```
icm> 抓取 https://example.com 并总结内容
Graph: DNS_RESOLVE -> TCP_CONNECT -> TLS_HANDSHAKE -> HTTP_GET -> HTML_PARSE -> NLP_SUMMARIZE
[DNS_RESOLVE]    ip='104.18.27.120'
[HTTP_GET]       status_code=200
[HTML_PARSE]     title='Example Domain'
[NLP_SUMMARIZE]  此域名仅用于文档示例，无需授权，请勿用于实际操作。  ✅
```

### 多语言翻译

```
icm> translate hello to chinese
Result: 你好  ✅

icm> 把 hello world 翻译成中文
Result: 你好，世界  ✅

icm> 把 你好 翻译成日文
Result: こんにちは  ✅
```

### 真实 DNS + 公网 IP

```
icm> fetch https://httpbin.org/ip
[DNS_RESOLVE] ip='34.235.67.238'   ← 真实 DNS 解析
[HTTP_GET]    origin='38.150.15.31' ← 真实公网出口 IP  ✅
```

---

## 系统架构

```
用户输入自然语言意图（任意语言）
        ↓
   AMS 意图分解器 (DeepSeek API)
   同时提取执行参数（url/path/content/target_lang...）
        ↓
  CDM Capability Graph (networkx DAG)
        ↓
  ┌──────────────────────────────────────────┐
  │              原语执行器（24个）              │
  │                                          │
  │  网络：DNS_RESOLVE / TCP / TLS / HTTP ← 真实│
  │  文件：FILE_OPEN/READ/WRITE/CLOSE    ← 真实│
  │  NLP： NLP_TRANSLATE / NLP_SUMMARIZE ← 真实│
  │  渲染：HTML_PARSE                    ← 真实│
  │  其他：CSS/JS/WINDOW/TEXT/SESSION...       │
  └──────────────────────────────────────────┘
        ↓
     执行结果输出
```

**底层系统栈：**

```
ICM Shell (Python 3.10) + 24 primitives
        ↓
Linux 6.1.82 内核（最小化）
  BINFMT_ELF + FUTEX + PCI
  e1000 网卡 + TCP/IP 协议栈
  tmpfs /data 持久化目录
        ↓
QEMU x86-64 / 裸机
```

---

## 项目结构

```
icm-os/
├── core/
│   ├── primitive.py      # CapabilityPrimitive 基类
│   ├── registry.py       # 自动发现注册所有原语
│   ├── graph.py          # CapabilityGraph + GraphExecutor
│   └── validator.py      # GraphValidator
├── ams/
│   ├── decomposer.py     # IntentDecomposer + 参数提取
│   └── embeddings.py     # 语义嵌入（预留）
├── security/
│   ├── taint.py          # TaintTracker
│   └── policy.py         # PolicyEngine
├── primitives/
│   ├── stateless/
│   │   ├── network.py    # DNS/TCP/TLS/HTTP  ← 真实
│   │   ├── nlp.py        # TRANSLATE/SUMMARIZE ← 真实
│   │   ├── file.py       # FILE_*            ← 真实
│   │   ├── rendering.py  # HTML_PARSE        ← 真实
│   │   ├── text.py       # 文本处理
│   │   └── misc.py       # 其他
│   └── stateful/
│       ├── cache_layer.py
│       ├── file_state.py
│       └── session_store.py
├── gbt/
│   ├── lifter.py         # ARM64 → SIR
│   ├── synthesizer.py    # SIR → x86-64
│   ├── verifier.py       # 行为等价验证
│   └── translator.py     # 顶层接口
├── iso-build/
│   ├── build.sh          # 完整构建脚本
│   ├── rebuild_initrd.sh # 快速重建
│   ├── icm_shell.py      # ICM-OS Shell
│   └── grub/grub.cfg
├── cli.py                # 开发模式 CLI
└── main.py               # 基准测试
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
python3 cli.py
```

### 构建 ISO

```bash
sudo apt install -y build-essential gcc make xorriso \
    grub-pc-bin grub-common busybox-static \
    libelf-dev libssl-dev bc flex bison qemu-system-x86

chmod +x iso-build/build.sh && ./iso-build/build.sh
```

### 启动

```bash
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

---

## 原语列表（24个）

| 类别 | 原语 | 状态 |
|---|---|---|
| 网络 | `DNS_RESOLVE` `TCP_CONNECT` `TLS_HANDSHAKE` `HTTP_GET` `HTTP_POST` | ✅ 真实 |
| NLP | `NLP_TRANSLATE` `NLP_SUMMARIZE` `NLP_ENCODE` | ✅ 真实 |
| 文件 | `FILE_OPEN` `FILE_READ` `FILE_WRITE` `FILE_CLOSE` | ✅ 真实 |
| 渲染 | `HTML_PARSE` | ✅ 真实 |
| 渲染 | `CSS_LAYOUT` `JS_EXECUTE` `WINDOW_RENDER` | mock |
| 文本 | `UTF8_DECODE` `TEXT_LAYOUT` `SCROLL_INPUT` `SEARCH_INDEX` | mock |
| 其他 | `BOOKMARK_WRITE` | mock |
| 有状态 | `SESSION_STORE` `CACHE_LAYER` `FILE_STATE` | 实现 |

---

## 里程碑

| 阶段 | 状态 | 内容 |
|---|---|---|
| M1 | ✅ 完成 | 可启动 ISO + CDM + 网络（2026.03） |
| M2 | ✅ 完成 | 真实 DNS / HTTP / 多语言翻译（2026.03） |
| M3 | ✅ 完成 | FILE_READ/WRITE + HTML_PARSE + NLP_SUMMARIZE + 多语言意图（2026.03） |
| M4 | 📋 计划中 | DEPENDENCY_SCAN + SANDBOX_EXEC（运行任意代码无需配置环境） |
| M5 | 📋 计划中 | C/Rust 核心原语 + 性能优化 |
| M6 | 📋 计划中 | 稳定发行版 v1.0 |

---

## 未来愿景

**M4 核心功能：零配置运行任意程序**

```
icm> 运行这个 Python 文件 /data/app.py
→ DEPENDENCY_SCAN: 发现需要 numpy, flask
→ ENV_BUILD: 自动创建隔离环境并安装依赖
→ SANDBOX_EXEC: 在沙箱中运行
→ 返回输出结果

用户无需安装 Python、配置环境、处理依赖冲突。
```

---

## 技术选型

| 层 | 当前 | 未来 |
|----|------|------|
| 内核 | Linux 6.1.82 | 自研微内核 |
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
- 支持语言：**任意**（由 DeepSeek AMS 处理）

---

## 安全机制

- **TaintTracker**：四级污点标签（CLEAN / USER_INPUT / NETWORK / FILE_UNTRUSTED）
- **PolicyEngine**：`NoTaintToAMS` · `NoSensitiveDataExfiltration`

---

## 参考论文

- [jinac.vxni.ink](https://jinac.vxni.ink)
- [jinac.pages.dev](https://jinac.pages.dev)

---

## License

MIT License

---

*ICM-OS is a research prototype. Not for production use.*
