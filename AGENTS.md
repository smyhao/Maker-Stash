# AGENTS.md

## 协作规则

- 讨论问题时保持批判性分析，不要一味附和用户观点；需要指出潜在问题、逻辑漏洞和可改进点，并给出理由充分、表达简洁的推荐方案。
- 读取和写入文本文件时默认使用 UTF-8 编码。遇到中文显示异常时，优先判断是终端输出编码问题还是文件内容损坏，不要在未确认前批量改写文件。
- 在 PowerShell 中需要查看中文内容时，优先使用显式 UTF-8 读取方式，或先设置输出编码：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

## 扩展开发

- 开发扩展或扩展相关主干能力时，遵守 `docs/extensions/RULE.md`。
