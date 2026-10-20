# USQuant learning workspace instructions

- The user now wants detailed Chinese teaching explanations, overriding the previous English-only documentation preference for new learning material.
- Explain each meaningful executable line in newly authored or changed teaching code with Chinese comments. Explain purpose, input/output, units, timing and relevant pitfalls. Expand dense multi-statement lines for readability. Do not change behavior merely to add comments.
- Provide Chinese step-by-step guides and an index. JSON cannot contain comments: use a neighboring Chinese field guide. YAML and shell examples may use native comment syntax.
- Keep official `vendor/lean` source and license notices unchanged unless the user explicitly requests engine modifications. Use separate Chinese annotated examples and source-reading guides; never imply the entire upstream engine has already been translated.
- Preserve the future live-trading milestone, brokerage source and architecture. Current execution remains historical backtesting or explicitly authorized broker paper trading. Future interest in live trading is not authorization to enable real orders now.
- Preserve local secrets, data and MySQL contents. Never commit .env, account credentials or private runtime results.
- `legacy/` is reference only. The active engine is QuantConnect LEAN.
