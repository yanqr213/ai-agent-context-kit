# Contributing

感谢你愿意参与 `ai-agent-context-kit`。

## 开发原则

- 优先保持零运行时依赖。
- 新功能应有可复现的 CLI 行为和测试覆盖。
- 不要在测试、日志或文档中加入真实 token、私钥或生产凭证。
- 输出格式变化需要同步更新 README。

## 本地流程

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m ai_agent_context_kit.cli . --profile codex
```

## Pull Request 建议

- 描述使用场景和行为变化。
- 说明新增或更新的测试。
- 如果涉及安全检测，请说明误报/漏报权衡。
- 保持改动聚焦，避免无关格式化。

## English Notes

Please keep the project dependency-light and test CLI-visible behavior. Avoid committing real credentials. Update documentation when output schemas or command flags change.
