# ICM-OS

**Intent-Centric Meta-Operating System** — 面向 AI 驱动能力分解与生成式二进制翻译的研究原型。

> 论文全文见作者个人网站：[jinac](https://jinac.pages.dev)

---

## 概述

ICM-OS 是一个**意图驱动**的元操作系统：用自然语言描述意图，系统将其分解为**能力原语**并执行。

**四大核心方向（愿景）：**

1. **无限原语扩展** — 注册表缺少原语时，由 AI 生成新原语代码、动态加载并缓存到磁盘，供下次直接使用。  
2. **任意格式执行** — 用户提交各类文件（Python、Shell、Lua、自定义 DSL 等），由 AI 分析语义并转换执行（见 `SANDBOX_EXEC` 与 Python 运行时）。  
3. **任意语言意图** — 多语言自然语言输入，由 **AMS（意图分解）** 映射为原语与参数并执行。  
4. **AI 驱动环境管理** — 通过结构化环境描述（Env Patch）让 AI 安全地配置开发环境，无需直接修改系统文件，支持会话隔离、可回滚和持久化确认。

---

## 当前状态（v0.1 · 2026.03）

| 组件 | 状态 | 说明 |
|------|------|------|
| **Linux 内核** | ✅ | 6.1.x LTS，`iso-build/build.sh` 可构建可启动 ISO |
| **ICM Shell（Python）** | ✅ | `cli.py` / `iso-build/icm_shell.py`，DeepSeek AMS + 能力图执行，多原语 |
| **ICM Shell（C）** | ✅ **新** | `c-primitives/icm_shell`，关键词路由 + **AMS（curl→DeepSeek）**，无 Python 亦可交互 |
| **C 原语库** | ✅ **新** | `c-primitives/`：`FILE_*`、`SHELL_EXEC`、`DNS_RESOLVE`、`HTTP_GET`、`ams.c` |
| **initramfs / ISO** | ✅ | `iso-build/rebuild_initrd.sh` 打包静态 `icm_shell`、Python 运行时与网络配置 |
| **GBT（生成式二进制翻译）** | 🔧 | `gbt/`，ARM64→x86-64 等实验路径 |
| **动态原语生成（Python）** | ✅ | AI 生成原语、缓存至 `~/.icm-os/primitives` 或 ISO 内 `/data/primitives` |
| **SANDBOX_EXEC** | ✅ | 任意格式文件分析执行（Python 侧） |
| **Env Engine** | 📋 设计中 | 结构化环境管理，会话隔离，持久化确认 |

---

## 仓库结构（节选）

| 路径 | 含义 |
|------|------|
| `ams/`、`core/`、`primitives/`、`security/` | Python 运行时：CPR、能力图、策略、预定义原语 |
| `cli.py` | 本地开发用交互 CLI（Rich 界面） |
| `c-primitives/` | **C99 原语**与 **`icm_shell`**：`file_*`、`shell_exec`、`dns_resolve`、`http_get`、`ams.c` |
| `iso-build/` | 内核 / busybox / initramfs / GRUB ISO、`rebuild_initrd.sh` |
| `gbt/` | 语义提升与合成管线（实验） |
| `env-engine/` | （规划中）环境管理子系统：Env Patch、Session 环境、持久化逻辑 |

---

## 架构概览

```text
自然语言意图（任意语言）
↓
┌───────────────────────────────────────┐
│  AMS（意图分解，DeepSeek API）          │
│  Python: IntentDecomposer（cli/icm）   │
│  C: ams.c → curl POST /chat/completions │
└───────────────────────────────────────┘
↓
能力图（Python） / 单原语路由（C shell）
↓
┌───────────────────────────────────────┐
│  原语执行                              │
│  Python: GraphExecutor + 注册表原语    │
│  C: 按 primitive_id 调 FILE/DNS/HTTP/… │
└───────────────────────────────────────┘
↓
┌───────────────────────────────────────┐
│  Env Engine（环境管理）                 │
│  接收 Env Patch → 更新 Session 环境 →   │
│  注入到进程 → 可选持久化（用户确认）      │
└───────────────────────────────────────┘
↓
执行结果

ISO / QEMU 栈（典型）：

C icm_shell（静态，可选） / Python icm_shell.py（回退）
↓
Linux 6.1 + busybox + init（/data、网络、resolv）
↓
QEMU x86-64 / 裸机


---

快速开始

配置

git clone https://github.com/jinbohao1688/icm-os.git
cd icm-os
echo "DEEPSEEK_API_KEY=your_key_here" > .env

Python 开发模式

pip install -r requirements.txt
python3 cli.py

C 原语与 C shell（本地）

cd c-primitives
make icm_shell          # 生成静态链接 icm_shell（默认 -static）
export DEEPSEEK_API_KEY=your_key_here   # AMS 可选
make run                 # 或 ./icm_shell

依赖：网络调用 DeepSeek 时需系统具备 curl（AMS 通过子进程调用）。

构建 ISO

sudo apt install -y build-essential gcc make xorriso \
  grub-pc-bin grub-common wget \
  libelf-dev libssl-dev bc flex bison qemu-system-x86

chmod +x iso-build/build.sh && ./iso-build/build.sh

QEMU 启动（示例）

qemu-system-x86_64 \
  -kernel iso-build/work/iso/boot/vmlinuz \
  -initrd iso-build/work/initrd.img \
  -append "console=ttyS0,115200n8 rdinit=/init" \
  -m 1024M -nographic \
  -netdev user,id=net0 -device e1000,netdev=net0

重建 initramfs

bash iso-build/rebuild_initrd.sh

重建后 init 优先 exec /bin/icm_shell，否则回退 python3 /icm-os/icm_shell.py，再 /bin/sh。


---

演示片段（概念）

Python CLI（cli.py）

自然语言意图 → AMS 分解 → 能力图执行；支持抓取、翻译、文件、动态原语等（见仓库内基准与 primitives/）。

C Shell（c-primitives/icm_shell）

关键词：read file、write、list/ls、dns/resolve、fetch/http、!command

设置 DEEPSEEK_API_KEY 后，其余行可走 AMS → 返回 JSON 中的 primitive + params，再调用对应 C 原语。



---

预定义原语（Python 侧 · 节选）

类别	示例原语

执行	SANDBOX_EXEC
网络	DNS_RESOLVE、HTTP_GET、HTTP_POST、…
NLP	NLP_TRANSLATE、NLP_SUMMARIZE、…
文件	FILE_READ、FILE_WRITE、…


完整列表以 primitives/ 与注册表为准。

C 原语（c-primitives/）

符号	作用

icm_file_read / icm_file_write / icm_file_list	文件读写与目录
icm_shell_exec	fork+execvp，合并 stdout/stderr
icm_dns_resolve	getaddrinfo + inet_ntop
icm_http_get	裸套接字 HTTP/1.1 GET（无 TLS）
icm_ams_decompose	curl 调 DeepSeek，解析返回 JSON



---

Env Engine：AI 驱动的环境管理

核心理念

AI 不应直接执行 shell 命令修改系统环境（如 export PATH），而应输出结构化环境描述，由系统安全地应用。Env Engine 正是为此设计：将环境配置抽象为 Env Patch，实现会话隔离、可回滚、可持久化确认。

环境模型

环境以 JSON 表示，而非 shell 脚本：

{
  "env": {
    "FLUTTER_HOME": "/opt/flutter"
  },
  "path": [
    "$FLUTTER_HOME/bin"
  ]
}

支持变量引用、PATH 追加/前置、变量设置/取消等操作。

Env Patch（AI 输出）

{
  "type": "env_patch",
  "operations": [
    {"op": "set", "key": "FLUTTER_HOME", "value": "/opt/flutter"},
    {"op": "append_path", "value": "$FLUTTER_HOME/bin"}
  ]
}

执行流程

Env Engine 接收 Patch，更新会话环境 JSON（/sessions/{id}/env.json）

程序运行时，Engine 注入环境变量到子进程（如通过 execve 或包装脚本）

支持 diff 预览和用户确认后才将环境持久化到系统配置文件（如 .bashrc），并提供回滚机制


安全约束

❌ 禁止直接写入 /etc 等系统目录

❌ 禁止完全覆盖关键变量（如 PATH）

✅ 操作白名单，执行前验证

✅ 会话隔离，不污染系统


示例：Flutter SDK 配置

用户意图： “配置 Flutter SDK”

AI 输出 Patch：（如上所示）

系统动作：

在会话环境中设置 FLUTTER_HOME=/opt/flutter

追加 $FLUTTER_HOME/bin 到 PATH

验证 flutter 命令可用性（可调用 SHELL_EXEC）

用户确认后，将变更写入 ~/.bashrc 并备份


未来扩展

多语言 SDK（Node.js、Python、Go 等）版本管理

容器化环境（Docker/Podman 后端）

跨架构执行（QEMU 集成）

完全可重现的环境描述



---

里程碑

阶段	状态	内容

M1–M5	✅	可启动 ISO、真实网络/文件、动态原语、SANDBOX_EXEC 等（见历史提交）
—	✅	C 原语 + C icm_shell + AMS(curl)、rebuild_initrd 集成
M6	📋	原语安全沙箱 + 依赖自动安装 + Env Engine 基础实现（会话环境、Patch 应用）
M7	📋	C/Rust 核心深化 + 性能优化 + Env Engine 持久化与回滚
M8	📋	稳定发行版 v1.0 + 完整环境管理能力



---

未来愿景（节选）

在任意语言/任意格式上「说意图即执行」，并配合本地或小型模型降低 API 依赖；运行时与沙箱向 Rust / Wasm 等方向演进。Env Engine 将实现 “AI 定义环境，系统安全构建”，让 ICM-OS 成为真正的 AI 原生开发平台。


---

技术选型

层	当前	方向

内核	Linux 6.1 LTS	可选自研或裁剪
意图分解	DeepSeek API（Python / C 经 curl）	本地小模型
运行时	Python 3.10 + 原语注册表	Rust + PyO3 / 原生扩展
C 原语	C99 + POSIX 与 ISO 静态链接	无 Python 启动路径
环境管理	（规划中）Python / C 实现	会话隔离 + 持久化 + 容器后端



---

参考论文

jinac.vxni.ink

jinac.pages.dev



---

License

MIT License


---

> ICM-OS 为研究原型，不用于生产环境关键业务。



---

