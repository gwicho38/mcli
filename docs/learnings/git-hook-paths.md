# Resolve hook paths through Git

A linked worktree has a `.git` pointer file, while default hooks are shared by its
owning repository. A configured `core.hooksPath` can replace that location. Looking
for `.git/hooks` in the current directory rejected valid worktrees and installed
in the wrong place when hooks were configured elsewhere.

The installer resolves the worktree root, then asks Git for its absolute effective
hook directory from that root. Anchoring the second query matters for relative
configuration when invoked from a subdirectory. Git and filesystem errors remain
nonzero. The hook script and preflight policy are unchanged.

Temporary repositories reproduce the linked worktree and both relative/absolute
configured-path failures before the fix. They verify actual hook contents and
executable mode without running CI or changing user repositories. A fake `.git`
folder is not a valid Git fixture; the existing normal-repository test now uses
`git init`. See tests/unit/workflow/test_ci_cli.py and release 8.0.72.

**Before**
```mermaid
flowchart LR
    Current[Current directory] --> Guess[Local .git/hooks]
    Guess --> Wrong[Missing or ineffective hook]
```

**After**
```mermaid
flowchart LR
    Current[Current directory] --> Git[Git resolves root and effective hooks]
    Git --> Hook[Executable hook at the configured path]
```
