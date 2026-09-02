# dsvideo-plugin

电商短视频插件，适用于 Codex 与 Claude Code。给产品图和卖点，按 MiniMax-H3 写出片。

主路走你自己的 ComfyUI（[comfy-mcp](https://github.com/Comfy-Org/comfy-mcp)），连不上再走 MiniMax 按量 API。

## 安装

本机需要已安装 `comfy-mcp`：

```bash
pip install comfy-mcp "comfy-cli>=1.14.0"
```

### Codex

```bash
codex plugin marketplace add ZMGID/dsvideo-plugin
codex plugin add dsvideo-plugin@dsvideo
```

装完在 `~/.codex/config.toml` 把 ComfyUI 地址写上（要带 `command`，不能只写 env）：

```toml
[mcp_servers.comfy-mcp]
command = "comfy-mcp"

[mcp_servers.comfy-mcp.env]
COMFYUI_URL = "http://127.0.0.1:8188"
```

把地址改成你的 ComfyUI。重启 Codex 开一个新会话。

### Claude Code

```
/plugin marketplace add ZMGID/dsvideo-plugin
```

```
/plugin install dsvideo-plugin@dsvideo
```

分两条消息发出去。装完把插件里的 `COMFYUI_URL` 改成你的 ComfyUI 地址。

## 用法

把产品图、卖点发给 agent 即可。

## License

[MIT](LICENSE)。`h3-prompt-writing` 与 `mmx-h3-video` 为 MiniMax 官方技能原文。
