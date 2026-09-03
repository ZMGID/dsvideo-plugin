# dsvideo-plugin

视频生成插件，适用于 Codex 与 Claude Code。用户只要提出生成视频、图片转视频或商品视频，默认由 dsvideo 使用内置 MiniMax-H3 工作流出片，不需要先点名插件。

主路走你自己的 ComfyUI（[comfy-mcp](https://github.com/Comfy-Org/comfy-mcp)），连不上再走 MiniMax 按量 API。

插件内置已经解析好的三分支 ComfyUI 工作流和自动配置脚本。AI 不需要临时研究 82 个节点、分支开关或服务器枚举；只需上传本机素材，脚本按图片数量自动选择 T2VA、单图 Ref2VA 或多图 Ref2VA，填入提示词、素材、比例和时长后提交。

API 备选链路由插件内置的零第三方依赖 Python 客户端直接调用 MiniMax 官方 Video Generation V2 API，不依赖 `mmx-cli`。默认使用国区官方 `https://api.minimax.cn`；国际账号才设置 `MINIMAX_REGION=global`。付费创建任务时必须明确选择 `768P` 或 `2K`；客户端提交前显示真实请求规格，成功后再核对返回的分辨率与时长。使用备选链路前，请在宿主环境安全配置 `MINIMAX_API_KEY`；不要把密钥写进仓库或发到聊天中。

## 安装

把这段发给 AI：

```text
按 https://raw.githubusercontent.com/ZMGID/dsvideo-plugin/main/skills/ecom-h3-video/SETUP.md 安装并配置 dsvideo-plugin
```

它会按你用的 Codex 或 Claude Code 安装插件。插件已内置公司局域网 ComfyUI 地址 `http://192.168.1.171:8188`。

或者自己装。本机需要 `comfy-mcp`：

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

把产品图、卖点发给 agent 即可。

## License

[MIT](LICENSE)。`h3-prompt-writing` 来源于 MiniMax 官方技能；`minimax-h3-api` 是本插件基于 MiniMax 官方 V2 API 维护的调用适配层。
