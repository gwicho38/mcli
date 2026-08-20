# Development Roadmap

## Current State
- **Version**: v8.0.62.
- **Key Features**: Universal script runner (`mcli run`), lazy command discovery, script→JSON sync (auto-detect language + metadata), versioned workflows with IPFS/Storacha sync, scheduler/daemon, AI chat, ML/trading dashboards.
- **Recent Updates**: Friendly runtime errors for crashing workflow scripts (PR #216), CI act-first preflight gate, seed base runtime into isolated venvs, stale global venv recreation.

## Planned Enhancements (Next 3–6 Months)

### High Priority
- [ ] **Orphaned-code removal** — Delete ~4.8K LOC of vestigial modules and dead auto-discovery paths (issue #209). Shrinks maintenance surface and clarifies the real registration path (`_add_lazy_commands()`).
- [ ] **Dependency consolidation** — Move unused core declarations (`anthropic`, `ollama`) to optional groups; clarify lazy-load boundaries.

### Medium Priority
- [ ] **Coverage uplift** — Raise minimum from 30% → 50%+; add real property-based tests (currently empty `tests/property/`).
- [ ] **Documentation** — ADRs for lazy loading, constants enforcement, and IPFS versioning; workflow tutorials (scheduler, daemon, sync); public CLI API reference; config-precedence guide.

### Technical Debt
- [ ] **Auto-discovery cleanup** — Auto-discovery is effectively dead code; commands register via `_add_lazy_commands()`. Remove the misleading scan paths.
- [ ] **Config precedence** — Document and simplify project → home → env override rules across TOML/ENV/YAML.

## Future Considerations
- **Feature Ideas**: Richer drag-and-drop authoring UX; broader script-language support; team workflow registries over IPFS.
- **Scalability**: Profile lazy-loading effectiveness; benchmark Rust extensions vs pure Python; optimize workflow-runtime hot paths and memory under concurrency.

---
**Effort Scale**: `S`: 2-3 days | `M`: 1 week | `L`: 2+ weeks
*Assessment based on project analysis performed 2026-06-26*
