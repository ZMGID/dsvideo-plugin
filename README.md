# dsvideo-plugin

视频生成插件，适用于 Codex 与 Claude Code。用户只要提出生成视频、图片转视频或商品视频，就由 dsvideo 接管，不需要先点名插件。

也可以把本机视频或单条视频链接交给 dsvideo 做参考拆解。插件通过 `mcp-video-analyzer` 提取时间线、关键帧、字幕和画面文字，再整理成电商视角的节奏、镜头、卖点表达与可复用创意结构。分析报告会先给用户检查；只有用户确认后才保存为独立参考模板，不会混入已经成片验证的 H3 工作流模板，也不会因为分析视频而自动开始生成。

每次生成前先让用户选择 `1. 本地 ComfyUI`、`2. MiniMax API` 或 `3. Grok API`，不默认选择任何一条路线。MiniMax 会先查询余额并报价；Grok 会显示三档美元报价，余额需在 xAI Console 查看。导演方案完成后先向用户展示最终剧本；只有用户看过并明确确认当前版本，才准备对应模型提示词并提交生成，剧本修改后需要重新确认。

插件内置已经解析好的三分支 ComfyUI 工作流和自动配置脚本。AI 不需要临时研究 73 个节点、分支开关或服务器枚举；只需上传本机素材，脚本按图片数量自动选择 T2VA、单图 Ref2VA 或多图 Ref2VA，填入提示词、素材、比例和时长后提交。

插件还包含通用 `video-director` Skill：先把一句想法、故事或图片整理成可执行的核心概念、完整时间线、镜头、动作、剪辑和声音方案，再由 `h3-prompt-writing` 转换成 H3 提示词。它不限定商品题材，也不要求用户先选择固定创作模式。

API 链路由插件内置的零第三方依赖 Python 客户端直接调用，不依赖额外 CLI。MiniMax H3 的模型和国区 URL 固定，安装时只需录入 API Key；Grok 或其他兼容接口录入 URL 与 API Key后，配置工具会调用 `/v1/models` 拉取生视频模型供用户选择。所有供应商统一保存在当前用户的 `dsvideo/providers.json`，不会写入仓库或插件缓存；旧的 `MINIMAX_API_KEY`、`XAI_API_KEY`、`XAI_API_BASE` 环境变量仍兼容且优先级更高。

## 安装

把这段发给 AI：

```text
按 https://raw.githubusercontent.com/ZMGID/dsvideo-plugin/main/skills/ecom-h3-video/SETUP.md 安装并配置 dsvideo-plugin
```

它会按你用的 Codex 或 Claude Code 安装插件，然后询问是否配置 MiniMax、Grok/兼容视频 API，并自动拉取可选模型。插件已内置公司局域网 ComfyUI 地址 `http://192.168.1.171:8188`。

或者自己装。本机需要 Node.js 22.12 或更高版本（参考视频分析使用固定版本 `mcp-video-analyzer@0.10.0`），以及 `comfy-mcp`：

```bash
pip install comfy-mcp "comfy-cli>=1.14.0"
```

### Codex

```bash
codex plugin marketplace add ZMGID/dsvideo-plugin
codex plugin add dsvideo-plugin@dsvideo
```

装完重启 Codex，开一个新会话。

### Claude Code

```
/plugin marketplace add ZMGID/dsvideo-plugin
```

```
/plugin install dsvideo-plugin@dsvideo
```

分两条消息发出去。插件已经带好公司局域网 ComfyUI 地址。

## 用法

把产品图、卖点发给 agent 即可。要拆解参考视频时，发送本机视频或单条视频链接并说“分析这个视频”；分析完成后可以要求把确认过的结构保存为参考模板。

## License

[MIT](LICENSE)。`video-director` 负责通用导演方案，`h3-prompt-writing` 来源于 MiniMax 官方技能；`minimax-h3-api` 与 `grok-video-api` 分别是 MiniMax V2 和 xAI Grok Imagine Video 官方 API 的调用适配层。
