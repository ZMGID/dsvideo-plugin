# 为 Codex 安装 dsvideo-plugin（克隆 + 符号链接）

这是备用安装路径。推荐方式见仓库根 [README.md](../README.md)：`npx skills add ZMGID/dsvideo-plugin -a codex -g`，或官方 `codex plugin marketplace add`。

Codex 会扫描 `~/.agents/skills`（`~/.codex/skills` 仍可用，但已弃用）。克隆并做符号链接即可被发现。

**克隆 / 符号链接不会自动加载仓库根的 `.mcp.json`。** 技能装好后，仍须在 `~/.codex/config.toml` 里配置 `comfy-mcp`。

## 前置

- Git
- 跑 Codex 的那台机器上已安装 `comfy-mcp`：

```bash
pip install comfy-mcp "comfy-cli>=1.14.0"
```

## 安装

1. **克隆仓库：**

   ```bash
   git clone https://github.com/ZMGID/dsvideo-plugin.git ~/.codex/dsvideo-plugin
   ```

2. **把 `skills` 链到 Codex 扫描目录：**

   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/dsvideo-plugin/skills ~/.agents/skills/dsvideo-plugin
   ```

   **Windows（PowerShell）：**

   ```powershell
   New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
   cmd /c mklink /J "$env:USERPROFILE\.agents\skills\dsvideo-plugin" "$env:USERPROFILE\.codex\dsvideo-plugin\skills"
   ```

3. **配置 MCP**（本步骤不会随符号链接自动完成）。编辑 `~/.codex/config.toml`，把占位符换成机柜 GPU 的局域网 IP 或主机名：

   ```toml
   [mcp_servers.comfy-mcp]
   command = "comfy-mcp"

   [mcp_servers.comfy-mcp.env]
   COMFYUI_URL = "http://REPLACE_WITH_GPU_HOST:8188"
   ```

   不要改成 Comfy Cloud 的 HTTP MCP。不要把真实局域网 IP 或密钥提交进本仓库。

4. **重启 Codex**（退出并重新启动 CLI），以便发现技能。

## 技能

- **ecom-h3-video** — 流水线入口：收集产品图 / 卖点 / 规格 → 写 H3 提示词 → 主路 Comfy / 备选 API
- **h3-prompt-writing** — MiniMax-H3 提示词结构（上游原文）
- **mmx-h3-video** — MiniMax 按量 API 备选（上游原文）

## 验证

```bash
ls -la ~/.agents/skills/dsvideo-plugin
```

应看到指向 `~/.codex/dsvideo-plugin/skills` 的符号链接（Windows 上为 junction），其下有 `ecom-h3-video`、`h3-prompt-writing`、`mmx-h3-video`。

## 更新

```bash
cd ~/.codex/dsvideo-plugin && git pull
```

技能经符号链接即时生效。改过 `config.toml` 后重启 Codex。

## 卸载

```bash
rm ~/.agents/skills/dsvideo-plugin
```

可选删除克隆：`rm -rf ~/.codex/dsvideo-plugin`。并从 `~/.codex/config.toml` 去掉 `comfy-mcp` 段。
