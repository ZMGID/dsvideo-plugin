# 内置 ComfyUI 工作流映射

正常出片不要读取本文件，不要重新分析节点；直接运行 `scripts/prepare_workflow.py`。只有维护内置工作流或脚本报告节点不匹配时才读。

## 固定来源

- 插件资产：`assets/minimax-h3-workflow.json`
- 来源工作流：`【Work-Fisher】Minimax-H3 整合流程.json`
- 保存时结构：ComfyUI UI 格式，73 个节点，三条并行分支
- 局域网 ComfyUI：`http://192.168.1.171:8188`

## 自动分支

| 输入 | 分支组 | 提示词 | 时长 | 画幅 | Conditioning | task_type | 图片节点 |
|---|---|---:|---:|---:|---:|---|---|
| 0 张图 | `文生图1` | 234 | 236 | 235 | 307 | `T2VA` | 无 |
| 1 张图 | `单图参考1` | 312 | 323 | 313 | 333 | `Ref2VA` | 335 |
| 2–3 张图 | `多图参考1` | 339 | 350 | 340 | 363 | `Ref2VA` | 362、364、365 |

服务器 `MiniMaxH3AudioConditioningT8.task_type` 的标准枚举是 `auto`、`T2VA`、`I2VA`、`FL2VA`、`L2VA`、`Ref2VA`、`Hybrid`。保存工作流中的 `T2VA — 文生音视频` 和 `Ref2VA — 参考生音视频` 是旧显示值，准备脚本会改成标准短枚举。

节点 215 `Fast Groups Bypasser (rgthree)` 只用于前端切换。准备脚本直接切换三组节点的 `mode`，并在输出中移除节点 215、Markdown 说明节点、未接线的音频节点及未使用的第三张图片节点。

## 刷新

服务器工作流确实改过节点或接线时，维护者才运行：

```text
python scripts/fetch_saved_workflow.py assets/minimax-h3-workflow.json
```

刷新后运行测试；若节点 ID 改变，同步更新 `prepare_workflow.py` 中的 `BRANCHES`。
