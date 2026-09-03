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

## 2. ComfyUI 地址

插件已内置公司局域网 ComfyUI 地址 `http://192.168.1.171:8188`，员工无需另外配置。

不要把 URL 以外的密钥写进仓库；聊天里不要回显 API key。

MiniMax 按量 API 只是 ComfyUI 失败后的备选链路，不要求安装 `mmx-cli`。第一次使用该备选链路前，让用户在宿主环境中安全设置 `MINIMAX_API_KEY`。插件默认国区，通过官方 `https://api.minimax.cn` 调用；只有国际账号才设置 `MINIMAX_REGION=global`。每次付费创建任务都必须明确选择 `768P` 或 `2K`，插件不会默认分辨率。不要代用户把 API key 写进本仓库、插件缓存或聊天记录。

## 3. 收尾

告诉用户：装好了；重启 Codex / 新开 Claude 会话；开口把产品图和卖点丢过来即可。
