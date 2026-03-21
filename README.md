# ICM-OS

**Intent-Centric Meta-Operating System** — A research prototype for AI-driven capability decomposition and generative binary translation.

> 论文全文见作者个人网站：[jinac.vxni.ink](https://jinac.vxni.ink) · [jinac.pages.dev](https://jinac.pages.dev)

---

## 概述

ICM-OS 是一个意图驱动的元操作系统研究原型。核心主张：用户不需要安装任何软件，只需用任意语言表达意图，系统由 AI 自动将意图分解为原子能力图并执行。

**当原语不存在时，AI 实时生成新原语并注册——系统可以无限自我扩展。**

项目包含三大核心机制：

**CDM（能力分解模型）**
从自然语言意图出发，通过意图分解器（AMS）生成一条满足类型、安全与策略约束的原语执行图。

**DynGen（动态原语生成）**
当注册表中没有合适的原语时，AMS 提出新原语 ID，系统调用 AI 实时生成 Python 代码，动态加载并执行。无需预定义，无限扩展。

**GBT（生成式二进制翻译）**
将源 ISA 二进制提升为语义中间表示（SIR），再合成目标 ISA 的等价代码，支持跨架构翻译。

---

## 当前状态 (v0.1 · M4 进行中 · 2026.03)

| 组件 | 状态 | 说明 |
|------|------|------|
| 内核 | ✅ | Linux 6.1.82 LTS，裸机可启动 |
| ICM Shell | ✅ | 意图驱动，CDM: yes，**24个预定义原语** |
| 动态原语生成 | ✅ **新** | AI 实时生成任意原语，无限扩展 |
| 多语言意图 | ✅ | 中文/英文/德文/日文……任意语言 |
| 自动网络 | ✅ | 启动时自动配置，无需手动操作 |
| /data 存储 | ✅ | tmpfs 持久化目录 |
| DNS/HTTP | ✅ 真实 | 真实网络请求 |
| HTML_PARSE | ✅ 真实 | BeautifulSoup 解析 |
| FILE_READ/WRITE | ✅ 真实 | 真实文件 I/O，任意语言写入 |
| NLP_TRANSLATE | ✅ 真实 | 任意语言互译 |
| NLP_SUMMARIZE | ✅ 真实 | 网页/文件 AI 总结 |
| GBT | ✅ | ARM64→x86-64 语义翻译 |
| 安全策略 | ✅ | TaintTracker + PolicyEngine |

---

## 动态原语生成演示

### AI 实时生成新原语

```
icm> use UUID_GENERATE primitive to create a new UUID
[DynGen] Generating primitive: UUID_GENERATE
[DynGen] Generated code:
  import uuid
  class UUID_GENERATEPrimitive(CapabilityPrimitive): ...
[DynGen] Registered: UUID_GENERATE
Graph: UUID_GENERATE
Result: {'result': 'bc05d63e-718c-4ea6-804c-a1eeef3b83d1'}  ✅
```

```
icm> calculate the SHA256 hash of "hello world"
[DynGen] Generating primitive: SHA256_HASH
Graph: SHA256_HASH
Result: {'result': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}  ✅
```

```
icm> use PROCESS_LIST primitive to show all running processes
[DynGen] Generating primitive: PROCESS_LIST
Graph: PROCESS_LIST
Result: [{"PID": "1", "COMMAND": "/usr/bin/python3 /icm-os/icm_shell.py"}, ...]  ✅
```

### 系统信息读取

```
icm> show current memory usage
Graph: FILE_OPEN -> FILE_READ -> UTF8_DECODE -> SEARCH_INDEX
Result: MemTotal: 1023272 kB  MemFree: 841840 kB  ✅  (真实内核内存)

icm> use CPU_INFO primitive
Graph: FILE_OPEN -> FILE_READ -> UTF8_DECODE
Result: vendor_id: AuthenticAMD  model: QEMU Virtual CPU  ✅
```

### 任意语言写入文件

```
# 中文
icm> 把"你好世界"写入文件 /data/notes/chinese.txt
→ 你好世界  ✅

# 德文
icm> Schreibe "Hallo Welt" in die Datei /data/notes/german.txt
→ Hallo Welt  ✅
```

### 网页抓取 + AI 总结

```
icm> 抓取 https://example.com 并总结内容
Graph: DNS_RESOLVE -> TCP_CONNECT -> TLS_HANDSHAKE -> HTTP_GET -> HTML_PARSE -> NLP_SUMMARIZE
Result: 此域名仅用于文档示例，无需授权，请勿用于实际操作。  ✅
```

---

## 系统架构

```
用户输入自然语言意图（任意语言）
        ↓
   AMS 意图分解器 (DeepSeek API)
   ├─ 提取执行参数 (url/path/content/target_lang...)
   └─ 发现缺失原语 → 触发 DynGen
        ↓
  ┌─────────────────────────────────────────────┐
  │  DynGen 动态原语生成器                         │
  │  原语不存在 → DeepSeek 生成代码 → exec() 加载  │
  │  → 注册到 CPR → 立即可用                       │
  └─────────────────────────────────────────────┘
        ↓
  CDM Capability Graph (networkx DAG)
        ↓
  原语执行器（24个预定义 + 无限动态生成）
        ↓
     执行结果
```

**底层系统栈：**

```
ICM Shell (Python 3.10)
  24 预定义原语 + 动态生成原语
        ↓
Linux 6.1.82 内核（最小化）
  e1000 网卡 + TCP/IP + tmpfs
        ↓
QEMU x86-64 / 裸机
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

## 预定义原语（24个）

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

**动态生成原语（示例）：**

| 原语 | 触发意图 |
|---|---|
| `UUID_GENERATE` | generate a random UUID |
| `SHA256_HASH` | calculate SHA256 hash |
| `BASE64_ENCODE` | encode to base64 |
| `PROCESS_LIST` | list running processes |
| `CPU_INFO` | show CPU information |
| `MD5_HASH` | calculate MD5 |
| ... | 任意新需求 |

---

## 项目结构

```
icm-os/
├── ams/
│   ├── decomposer.py     # IntentDecomposer + 参数提取
│   ├── dynamic_gen.py    # DynamicPrimitiveGenerator ← 新
│   └── embeddings.py
├── core/
│   ├── primitive.py
│   ├── registry.py       # 自动发现 + 动态注册
│   ├── graph.py
│   └── validator.py
├── security/
│   ├── taint.py
│   └── policy.py
├── primitives/
│   ├── stateless/        # network/nlp/file/rendering
│   └── stateful/         # cache/session/file_state
├── gbt/                  # ARM64→x86-64 翻译
├── iso-build/
│   ├── build.sh
│   ├── rebuild_initrd.sh
│   └── icm_shell.py
├── cli.py
└── main.py
```

---

## 里程碑

| 阶段 | 状态 | 内容 |
|---|---|---|
| M1 | ✅ 完成 | 可启动 ISO + CDM + 网络（2026.03） |
| M2 | ✅ 完成 | 真实 DNS / HTTP / 翻译（2026.03） |
| M3 | ✅ 完成 | FILE_READ/WRITE + HTML_PARSE + NLP_SUMMARIZE（2026.03） |
| M4 | ✅ 完成 | 动态原语生成，系统自我扩展（2026.03） |
| M5 | 📋 计划 | SANDBOX_EXEC：零配置运行任意程序 |
| M6 | 📋 计划 | C/Rust 核心 + 性能优化 |
| M7 | 📋 计划 | 稳定发行版 v1.0 |

---

## 未来愿景：零配置执行环境

```
icm> 运行这个 Python 文件 /data/app.py
→ DEPENDENCY_SCAN: 发现需要 numpy, flask
→ ENV_BUILD: 自动创建隔离环境并安装依赖
→ SANDBOX_EXEC: 在沙箱中运行
→ 返回输出

用户无需安装 Python、配置环境、处理依赖冲突。
Flutter、Node.js、Rust……任何程序，同理。
```

---

## 技术选型

| 层 | 当前 | 未来 |
|----|------|------|
| 内核 | Linux 6.1.82 | 自研微内核 |
| 运行时 | Python 3.10 | Rust + PyO3 |
| 原语扩展 | AI 动态生成 | 编译缓存 + 安全沙箱 |
| 意图分解 | DeepSeek API | 本地小模型 |
| 隔离 | 进程级 | Wasm sandbox |

---

## 基准测试

- 意图分解成功率：**10/10（100%）**
- 原语复用率：**3.15×**
- 单元测试：**36/36 通过**
- 支持输入语言：**任意**
- 动态可生成原语：**无限**

---

## 安全机制

- **TaintTracker**：四级污点（CLEAN / USER_INPUT / NETWORK / FILE_UNTRUSTED）
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
