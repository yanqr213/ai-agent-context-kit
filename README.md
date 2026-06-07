# ai-agent-context-kit

`ai-agent-context-kit` 是一个零运行时依赖的 Python CLI，用来把一个代码仓库整理成可控大小、可审计、可复现的 AI 编程上下文包。

它面向使用 Codex、Claude Code、ChatGPT、Cursor 等 AI 编程工具的开发者：当你需要让模型快速理解一个仓库时，可以先生成一份 Markdown bundle 和 JSON manifest，而不是在每个会话里反复解释项目背景。

## 适用场景

- 新开 AI 编程会话前，快速提供仓库结构、关键源码和约束。
- 在团队中共享“这次要给 AI 的上下文”，让输入可审计、可复现。
- 给 Codex 或 Claude Code 准备不同预算的上下文包。
- 在 CI 中检查上下文包是否会包含大文件、二进制文件或潜在密钥。
- 为 issue、PR、外包协作或代码审查生成最小可用项目背景。

## 功能

- 扫描仓库文件并生成 Markdown 上下文包。
- 生成 JSON manifest，记录 included/excluded 文件、预算、hash、警告和筛选条件。
- 遵守 `.gitignore` 风格忽略规则，并内置常见目录和二进制类型排除。
- 支持按扩展名、路径 glob、最大文件大小筛选。
- 支持字符预算和简易 token 预算估算。
- 默认排除大文件、二进制文件和疑似密钥文件。
- 提供 `generic`、`codex`、`claude`、`claude-code` 输出 profile。
- 仅使用 Python 标准库，适合离线和 CI 环境。

## 安装

需要 Python 3.9 或更新版本。

开发模式安装：

```bash
python -m pip install -e .
```

也可以不安装，直接从源码运行：

```bash
python -m ai_agent_context_kit.cli --help
```

安装后可使用：

```bash
aictx --help
```

## 快速开始

在仓库根目录运行：

```bash
aictx . --profile codex
```

默认会生成：

```text
.aictx/context-bundle.md
.aictx/context-bundle.manifest.json
```

给 Claude Code 生成较小上下文：

```bash
aictx . --profile claude-code --token-budget 40000 --include-ext py,md,toml,json
```

只收集源码和文档，排除测试快照：

```bash
aictx . \
  --include-ext py,md,yml,toml \
  --exclude-path "tests/fixtures/*" \
  --exclude-path "*.snapshot"
```

在安全检查中发现疑似密钥时让 CI 失败：

```bash
aictx . --fail-on-secret
```

## 命令参数

```text
aictx [ROOT]
  -o, --output-dir DIR        输出目录，默认 .aictx
  --name NAME                 输出文件 basename，默认 context-bundle
  --profile PROFILE           generic / codex / claude / claude-code
  --include-ext EXT           只包含扩展名，可重复或逗号分隔
  --exclude-ext EXT           排除扩展名，可重复或逗号分隔
  --include-path GLOB         只包含匹配路径，可重复
  --exclude-path GLOB         额外排除路径，可重复
  --token-budget N            估算 token 预算，默认 120000
  --char-budget N             字符预算
  --max-file-bytes N          单文件大小上限，默认 524288
  --no-gitignore              不读取仓库 .gitignore
  --include-secret-files      包含疑似密钥文件，但写出警告
  --fail-on-secret            检测到疑似密钥时返回非零状态
```

## 输出格式

Markdown bundle 包含：

- 仓库、生成时间、profile、预算摘要。
- Agent instructions，帮助 Codex/Claude Code 理解该 bundle 的使用方式。
- File index，列出路径、字节数、字符数、估算 token 和 SHA-256 前缀。
- Included files，每个文件以 fenced code block 形式展示。
- Warnings 和 Excluded files，用于审计被排除内容。

JSON manifest 包含：

```json
{
  "schema_version": "1.0",
  "tool": "ai-agent-context-kit",
  "profile": "codex",
  "repository": { "name": "repo", "root": "/path/to/repo" },
  "budgets": {
    "token_budget": 120000,
    "estimated_tokens": 1234,
    "truncated_by_budget": false
  },
  "included_files": [
    {
      "path": "src/app.py",
      "bytes": 1200,
      "sha256": "...",
      "estimated_tokens": 300
    }
  ],
  "excluded_files": [
    { "path": ".env", "reason": "potential secret (...)" }
  ],
  "warnings": []
}
```

## 隐私与安全边界

- 工具不会读取或请求 GitHub token，也不会推送 GitHub。
- 工具不会访问外部网络。
- 疑似密钥检测是启发式规则，不是完整安全扫描器。
- 默认会排除疑似密钥文件；如果使用 `--include-secret-files`，请在共享前人工审查输出。
- JSON manifest 中不会打印检测到的密钥值，只记录原因摘要。
- 生成的 Markdown bundle 可能包含源码和业务逻辑，请按内部安全规则保存和共享。

## CI 用法

示例 GitHub Actions 已包含在本仓库 `.github/workflows/ci.yml`：

```yaml
- name: Build context bundle
  run: python -m ai_agent_context_kit.cli . --fail-on-secret --token-budget 60000
```

这可以确保上下文包能够在干净环境中生成，并在潜在密钥被检测到时失败。

## 开发与测试

运行测试：

```bash
python -m unittest discover -s tests -v
```

运行 CLI：

```bash
python -m ai_agent_context_kit.cli . --profile codex --output-dir .aictx
```

## English

`ai-agent-context-kit` is a zero-runtime-dependency Python CLI for building auditable and reproducible prompt/context bundles from a repository.

It helps developers using Codex, Claude Code, ChatGPT, Cursor, and similar AI coding tools provide the right repository context without repeatedly explaining the project. The tool scans text files, respects `.gitignore`-style rules, applies extension/path filters, estimates character and token budgets, excludes large/binary/secret-like files by default, and writes both a Markdown bundle and a JSON manifest.

Basic usage:

```bash
python -m pip install -e .
aictx . --profile codex --token-budget 60000
```

Outputs:

```text
.aictx/context-bundle.md
.aictx/context-bundle.manifest.json
```

Security model:

- No network access is required.
- The tool does not read, request, print, or push GitHub tokens.
- Secret detection is heuristic and should not replace a dedicated security scanner.
- Secret-like files are excluded by default and reported through warnings.

CI example:

```bash
python -m unittest discover -s tests -v
python -m ai_agent_context_kit.cli . --fail-on-secret --token-budget 60000
```

## License

MIT. See [LICENSE](LICENSE).
