# archive-tui

Minimal Ratatui wizard for adding archive entries. Lavender theme (`#cba6f7` on `#11111b`).

Flow: category → title → year → cover url → date/author → rating → review → add → check → `vercel --prod` (only if add+check pass).

```bash
cargo build --release --manifest-path tui/Cargo.toml
./tui/target/release/archive-tui --root=. --no-deploy
./tui/target/release/archive-tui --root=.
```

Keys: `↑↓`/`jk` pick category, `1-4` quick pick, `Enter` next/submit, `Esc` back, `Ctrl+C` quit.
Flags: `--root=<dir>` archive dir (default `.`), `--no-deploy` skip vercel, `-h` help. Blank date = today IST.
