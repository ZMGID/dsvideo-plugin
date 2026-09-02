# dsvideo-plugin 安装与配置

> 给 Agent 读。用户把这份文件的路径或 URL 交给你，例如：
> `按 https://raw.githubusercontent.com/ZMGID/dsvideo-plugin/main/skills/ecom-h3-video/SETUP.md 安装并配置 dsvideo-plugin`

按下面三步做。宿主命令只跑一条路径，不要 Codex / Claude 都装。

## 1. 装插件（按用户正在用的宿主选一条，不要三条都跑）

- **Codex**：
  ```bash
  codex plugin marketplace add ZMGID/dsvideo-plugin
  codex plugin add dsvideo-plugin@dsvideo
  ```
- **Claude Code**：让用户分两条消息发 `/plugin marketplace add ZMGID/dsvideo-plugin` 和 `/plugin install dsvideo-plugin@dsvideo`，或你代跑等价 CLI：`claude plugin marketplace add ZMGID/dsvideo-plugin` 然后 `claude plugin install dsvideo-plugin@dsvideo`。
- **分不清宿主**：问一句是 Codex 还是 Claude Code。
- 本机需要 `pip install comfy-mcp "comfy-cli>=1.14.0"`（已有 `comfy-mcp` 命令就跳过）。

装完先停下来问第 2 节那一句，不要自己往下写配置。

## 2. 配 ComfyUI 地址（只问一次）

问：

```text
ComfyUI 地址？直接回 URL，例如 http://127.0.0.1:8188
```

用户没说就用 `http://127.0.0.1:8188`。

**Codex** 写入 `~/.codex/config.toml`（必须带 command，不能只写 env）：

```toml
[mcp_servers.comfy-mcp]
command = "comfy-mcp"

[mcp_servers.comfy-mcp.env]
COMFYUI_URL = "<用户给的地址>"
```

已有同名段则改 URL，不要复制第二份。

**Claude Code**：插件已带 `.mcp.json`，把安装副本或用户可见配置里的 `COMFYUI_URL` 改成这个地址。

不要把 URL 以外的密钥写进仓库；聊天里不要回显 API key。

## 3. 收尾

告诉用户：装好了；ComfyUI 指向哪；重启 Codex / 新开 Claude 会话；开口把产品图和卖点丢过来即可。
