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
- 本机需要 Node.js 22.12 或更高版本；参考视频分析 MCP 由插件通过 `npx` 按固定版本启动，首次使用需要联网下载依赖。
- 本机需要 `pip install comfy-mcp "comfy-cli>=1.14.0"`（已有 `comfy-mcp` 命令就跳过）。

## 2. 配置生视频接口

插件已内置公司局域网 ComfyUI 地址 `http://192.168.1.171:8188`，员工无需另外配置。安装后必须问用户一次：

```text
是否现在配置生视频 API？
1. MiniMax H3
2. Grok 或其他 OpenAI 兼容视频接口
3. 两种都配置
4. 暂不配置
```

等待用户选择，不默认配置。找到已安装插件根目录中的 `scripts/dsvideo_config.py`，用可隐藏输入的终端执行；API Key 不放进命令参数，也不在聊天或输出中回显。

- **MiniMax H3**：模型和国区 URL 已固定，只向用户收取 API Key，然后运行：
  ```bash
  python <插件根目录>/scripts/dsvideo_config.py set-minimax
  ```
- **Grok 或其他兼容接口**：向用户收取供应商简称、API URL 和 API Key，然后运行：
  ```bash
  python <插件根目录>/scripts/dsvideo_config.py set-provider --name <供应商简称> --base-url <API URL>
  ```
  脚本会自动请求 `<API URL>/v1/models`，优先列出生视频模型，让用户输入编号选择，并保存所选模型。URL 末尾带 `/v1` 也可以，脚本会自动规范化。Grok 的供应商简称必须使用 `grok`，这样现有 Grok 出片入口会直接读取它。

所有供应商统一保存到当前用户配置目录的 `dsvideo/providers.json`；Windows 通常是 `%APPDATA%\dsvideo\providers.json`。这是用户本地明文配置，不写入仓库或插件缓存。需要核对时运行 `python <插件根目录>/scripts/dsvideo_config.py show`，输出只显示 `<saved>`，不会显示 Key。

生成前仍由用户选择本地 ComfyUI、MiniMax 按量 API 或 Grok API，不自动切换路线。导演方案完成后必须先展示最终剧本，等用户确认当前版本后才执行生成；剧本修改后重新确认。MiniMax 选择界面显示真实余额及人民币估价；Grok 显示适用于所选服务的报价信息。每次付费创建仍必须明确选择对应分辨率。

## 3. 收尾

告诉用户：装好了；重启 Codex / 新开 Claude 会话；开口把产品图和卖点丢过来即可。
