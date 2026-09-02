# dsvideo-plugin

电商短视频出片插件，给 **Codex、Claude Code 以及同类编码代理** 用：用户提供产品图 + 卖点 + 平台规格，代理按 MiniMax-H3 结构写提示词并出片。

- **主路**：机柜局域网 RTX 3090 上的 ComfyUI，经官方本地 [comfy-mcp](https://github.com/Comfy-Org/comfy-mcp)（stdio）提交 / 等待 / 取片。
- **备选**：仅当 3090 队列满或局域网 Comfy 不可达时，走 MiniMax 按量 API（`mmx-h3-video` 技能）。API 备选假定本机 `PATH` 上已有 `mmx`。

本仓库不是 MiniMax Hub 应用，也不是桌面客户端。插件 id 为 `dsvideo-plugin`。

## 安装 Codex（推荐）

用 [Vercel skills CLI](https://github.com/vercel-labs/skills) 发现仓库根 `skills/*/SKILL.md`，装到用户级 Codex 技能目录（`~/.agents/skills/`）：

```bash
npx skills add ZMGID/dsvideo-plugin -a codex -g
```

该命令只装技能，**不会**写入 MCP。在跑 Codex 的那台机器上安装 `comfy-mcp`，并写入 `~/.codex/config.toml`：

```bash
pip install comfy-mcp "comfy-cli>=1.14.0"
```

```toml
[mcp_servers.comfy-mcp]
command = "comfy-mcp"

[mcp_servers.comfy-mcp.env]
COMFYUI_URL = "http://REPLACE_WITH_GPU_HOST:8188"
```

把 `REPLACE_WITH_GPU_HOST` 换成机柜 GPU 的局域网 IP 或主机名。不要改成 Comfy Cloud 的 HTTP MCP。不要把真实局域网 IP、API Key 或其它密钥提交进本仓库。

重启 Codex 后即可使用技能。

## 官方 Codex 插件（技能 + 捆绑 MCP）

仓库带 `.codex-plugin/plugin.json` 与 `.agents/plugins/marketplace.json`。此路径会加载 `skills/` **以及** 根目录 `.mcp.json`：

```bash
codex plugin marketplace add ZMGID/dsvideo-plugin
codex plugin add dsvideo-plugin@dsvideo
```

仍须本机有 `comfy-mcp`：

```bash
pip install comfy-mcp "comfy-cli>=1.14.0"
```

捆绑的 `.mcp.json` 里仍是占位符 `http://REPLACE_WITH_GPU_HOST:8188`。安装后：

1. **改安装副本**（推荐，改的是 Codex 实际加载的捆绑 MCP）：

   ```text
   ~/.codex/plugins/cache/dsvideo/dsvideo-plugin/<version>/.mcp.json
   ```

   `<version>` 为 `plugin.json` 的 semver（当前 `0.1.0`）。把其中的 `COMFYUI_URL` 换成真实 GPU 地址。

2. **或在 `~/.codex/config.toml` 写完整的用户级 MCP**（必须带 `command`，不能只写 `[mcp_servers.comfy-mcp.env]`——Codex 不会把 env 段合并进插件捆绑的服务器）：

   ```toml
   [mcp_servers.comfy-mcp]
   command = "comfy-mcp"

   [mcp_servers.comfy-mcp.env]
   COMFYUI_URL = "http://REPLACE_WITH_GPU_HOST:8188"
   ```

改完重启 Codex。

## 备用：克隆 + 符号链接

若不想用 skills CLI 或官方插件命令，见 [`.codex/INSTALL.md`](.codex/INSTALL.md)：克隆到 `~/.codex/dsvideo-plugin`，把 `skills` 链到 `~/.agents/skills/dsvideo-plugin`，并**单独**在 `config.toml` 里配 MCP（符号链接不会自动加载 `.mcp.json`）。

## 四件套（仅此，无其它）

| 件 | 路径 | 作用 |
| --- | --- | --- |
| 本插件流水线技能（骨架） | `skills/ecom-h3-video/` | 收集素材 → 写 H3 提示词 → 主路 Comfy / 备选 API |
| 官方 MiniMax 技能 | `skills/h3-prompt-writing/` | 从 [MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) 的 `.claude/skills/h3-prompt-writing/` **原文复制** |
| 官方 MiniMax 技能 | `skills/mmx-h3-video/` | 从 [MiniMax-AI/cli](https://github.com/MiniMax-AI/cli) 的 `skill/h3-video/` **原文复制**（本仓库目录名固定为 `mmx-h3-video`；上游 frontmatter 已是 `name: mmx-h3-video`，未改） |
| 官方本地 Comfy MCP | 根目录 `.mcp.json` | Comfy-Org 的 Python 包 `comfy-mcp`（`pip install`），**不是** npm `comfyui-mcp`，**不是** Comfy Cloud |

## 明确不包含

- MiniMax Hub、以及任何 Hub 工作流技能
- Comfy Cloud、`comfy-cloud` 插件/技能、HTTP 云端 MCP
- `minimalist-product-ad-generator` 或同类一键广告生成器
- `mmx-cli` 的安装、检测或 bootstrap（技能里不加安装步骤；仓库不提供 `bin/` 或 npm hook）

## 拓扑

```
编码代理所在机器                         机柜 GPU（用户自己启动）
┌─────────────────────────┐              ┌──────────────────────────┐
│  Codex / Claude Code /  │   LAN HTTP   │  ComfyUI                 │
│  同类代理               │─────────────►│  --listen 0.0.0.0        │
│  MCP 客户端: comfy-mcp  │ COMFYUI_URL  │  --port 8188             │
│  (stdio, 本机进程)      │              │  RTX 3090 + 已就位的 H3  │
└─────────────────────────┘              └──────────────────────────┘
```

`COMFYUI_URL` 只让 **提交 / 排队 / 上传 / 取结果** 打到远端 GPU。生命周期（启停 Comfy）和模型下载仍发生在 MCP 所在机器——权重必须已经在 3090 箱上。

GPU 箱上由用户自行启动 ComfyUI，例如：

```bash
# 在 3090 箱上，不要写进本仓库
<你的 ComfyUI 启动方式> --listen 0.0.0.0 --port 8188
```

## Claude Code

仓库仍是单插件 Claude marketplace（`marketplace.json` 与 `plugin.json` 同在 `.claude-plugin/`，插件 `source` 为仓库根 `./`）：

```bash
claude plugin marketplace add ZMGID/dsvideo-plugin
claude plugin install dsvideo-plugin@dsvideo
```

本地克隆调试：

```bash
git clone https://github.com/ZMGID/dsvideo-plugin.git
claude --plugin-dir ./dsvideo-plugin
```

Claude Code 会加载根目录 `.mcp.json`（`comfy-mcp` + `COMFYUI_URL`）。技能命名空间为 `/dsvideo-plugin:ecom-h3-video`（以及同插件下的 `h3-prompt-writing`、`mmx-h3-video`）。仍须把 `COMFYUI_URL` 换成真实 GPU 地址（安装缓存或本地克隆里的 `.mcp.json`）。

## 用法（短）

把产品图、卖点和（可选）平台/时长/画幅交给代理。代理应：

1. 按 `ecom-h3-video` 收集素材；平台细则未补时走通用电商卫生并标明「平台规则待补」。
2. 用 `h3-prompt-writing` 改写成 H3 结构（有图优先 I2VA）。
3. 经 comfy-mcp 在局域网 Comfy 上找 **本地免费 OSS** 的 MiniMax-H3 / H3 视频模板并出片。
4. 仅当 Comfy 不可达或队列满时，才用 `mmx-h3-video` 走按量 API。
5. 把成片路径或 URL 还给你。

## 布局

```
.codex-plugin/plugin.json          # Codex 插件清单（无 hooks）
.agents/plugins/marketplace.json   # Codex marketplace add 用
.codex/INSTALL.md                  # 克隆 + 符号链接备用说明
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
skills/ecom-h3-video/SKILL.md
skills/h3-prompt-writing/          # MiniMax-H3 原文
skills/mmx-h3-video/               # MiniMax-AI/cli skill/h3-video 原文
.mcp.json
README.md
LICENSE                            # 本插件 MIT
```

`.codex-plugin/` 与 `.claude-plugin/` 里只有清单；`skills/` 与 `.mcp.json` 在仓库根，不复制第二份技能树。

## 许可与致谢

本插件代码与文档（除下列原文复制文件外）为 MIT，见 [LICENSE](LICENSE)。

复制的官方技能文件保持上游原文（含 frontmatter），版权与许可归原作者：

- [MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) — `h3-prompt-writing`
- [MiniMax-AI/cli](https://github.com/MiniMax-AI/cli) — `skill/h3-video`（本仓库目录名 `mmx-h3-video`）
- [Comfy-Org/comfy-mcp](https://github.com/Comfy-Org/comfy-mcp) — 本地 Comfy MCP（Python / PyPI `comfy-mcp`）
