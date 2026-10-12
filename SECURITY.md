# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| Older commits / forks | ❌ best-effort only |

## Report a vulnerability

**Don't open a public issue for security bugs.** Email the maintainer directly:

- GitHub: [@MaithreshVaddi-27](https://github.com/MaithreshVaddi-27) (open a private security advisory on the repo if enabled, otherwise DM via a minimal non-sensitive issue asking for contact)

Include: what you found, which file/line, steps to reproduce, and impact.
Expect an acknowledgement within 72 hours and a fix or mitigation plan within 14 days.

## Scope notes (known limitations, not bugs)

- The Gradio UI has **no login by default**. Set `GRADIO_USERNAME` + `GRADIO_PASSWORD`
  to require login everywhere (local or shared); `GRADIO_SHARE=true` additionally
  refuses to start without them. Don't expose the UI to a network you don't trust
  without login.
- The per-user **rate limit is in-memory** (anti-double-click, not anti-abuse).
- Uploaded PDFs are validated by extension + `%PDF-` header + size cap, not by a full malware scan. Don't process untrusted PDFs on sensitive machines.
- Never commit `.env` or API keys. Rotate any exposed credential immediately at its provider (AI Studio / HuggingFace / Composio).
