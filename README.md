# dsvideo-plugin

Codex 电商短视频插件。交产品图 + 卖点，按 MiniMax-H3 出片。默认打局域网机柜 RTX 3090 上的 ComfyUI，GPU 忙了才走 MiniMax 按量 API。

## 安装

```bash
npx skills add ZMGID/dsvideo-plugin -a codex -g
pip install comfy-mcp "comfy-cli>=1.14.0"
```

在 `~/.codex/config.toml` 加上：

```toml
[mcp_servers.comfy-mcp]
command = "comfy-mcp"

[mcp_servers.comfy-mcp.env]
COMFYUI_URL = "http://你的机柜IP:8188"
```

GPU 那台机的 ComfyUI 要 `--listen 0.0.0.0 --port 8188`。改完重启 Codex。

## 用法

把产品图、卖点、平台规格丢给 Codex，它会写 H3 提示词并出片。

## 其他

Claude Code：

```bash
claude plugin marketplace add ZMGID/dsvideo-plugin
claude plugin install dsvideo-plugin@dsvideo
```

更多安装方式见 [.codex/INSTALL.md](.codex/INSTALL.md)。MIT。技能原文来自 [MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3)、[MiniMax CLI](https://github.com/MiniMax-AI/cli)；出片 MCP 用 [comfy-mcp](https://github.com/Comfy-Org/comfy-mcp)。
