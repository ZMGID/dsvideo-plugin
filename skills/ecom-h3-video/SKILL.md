---
name: ecom-h3-video
description: >
  把商品图片和简短要求制作成 MiniMax-H3 商品页展示视频，并复用已经验证的同类视频模板。
  用户要求商品页视频、Listing 视频、产品展示视频、H3 出片，或要保存/复用商品视频模板时使用。
  默认走局域网 ComfyUI；付费 MiniMax API 仅在用户明确选择后使用。
---

# 商品页 H3 视频

目标是准确、清楚地展示商品，不做带货口播、UGC 表演、营销剧情或购买 CTA。回复保持简短。

## 工作流程

1. 接收商品图和用户要求。缺少会改变成片的关键信息时只问必要问题；未指定时长或画幅，可以给出简短建议并说明假设。
2. 查看 `templates/*.json`（忽略 `_template.json`），按商品的展示方式、镜头目标、时长、画幅和参考图数量选择最接近的模板；品类名称只作辅助。没有合适模板时，读取 [references/product-page-directing.md](references/product-page-directing.md) 编排镜头。
3. 读取同级技能 `h3-prompt-writing`，把镜头方案写成对应的 H3 提示词。一张图走 I2VA/单图参考，多张图走多图参考，无图才走 T2VA。
4. 默认通过 `comfy-mcp` 使用 `http://192.168.1.171:8188` 上保存的 `【Work-Fisher】Minimax-H3 整合流程.json`。读取 [references/comfy-workflow-safety.md](references/comfy-workflow-safety.md)，只替换提示词、输入图片/视频、比例和时长，检查通过后提交并记录 `prompt_id`。
5. 找不到工作流或本地失败时只报告真实错误，不搜索替代模板、不推测模型问题、不自动改走付费 API。
6. 只有用户明确选择付费 API 时才读取同级技能 `minimax-h3-api`；提交前必须确认 `768P` 或 `2K`。

## 模板

- 模板复用镜头结构、节奏和提示词骨架；商品颜色、外形、文字、部件、功能和卖点仍以本次素材为准。
- 只有用户明确确认成片可用并要求“保存为模板”时，才参考 `templates/_template.json` 新建模板；不自动保存草稿。
- 模板写入本技能源码的 `templates/`，文件名使用简短英文小写连字符。若当前只有已安装缓存而没有插件源码，不写缓存，改为输出模板 JSON 交给维护者入库。
- 不保存 API Key、任务 ID、人员信息或本机素材绝对路径。模板不得包含或覆盖模型、步数、CFG、采样器、调度器等 ComfyUI 参数。

交付时只说明成片位置、使用的模板（若有）、模式、时长和画幅；不要输出冗长的内部分析。
