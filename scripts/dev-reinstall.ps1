$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$codexPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$cachebusterScript = Join-Path $env:USERPROFILE '.codex\skills\.system\plugin-creator\scripts\update_plugin_cachebuster.py'

& $codexPython -X utf8 $cachebusterScript $repoRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

codex plugin add dsvideo-plugin@dsvideo
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '完成。请新建一个 Codex 任务测试最新插件。'
