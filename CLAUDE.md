# csol (Asciiverse packaging)

Niels Sonnich Poulsen's collection of solitaire games in C89 with ncurses
(PDCurses on Windows); packaged for the Asciiverse catalog and as system
packages. Not our code: keep changes small, list every one in PATCHES.md,
and offer fixes upstream.

- Remotes: `upstream` is github.com/nielssp/csol, `origin` is
  github.com/theasciiverse/csol.
- Branch `asciiverse` = upstream master plus our commits. Tags carry the
  upstream commit's date past a release: `v1.6.0+20250719-av.1`.
- The games and themes are data files read at run time (`games/`,
  `themes/`, named in `csolrc`); a new game is a new file, no code. csol
  finds csolrc in the user's folder, then `/etc/xdg/csol`, then beside the
  program, then in the current folder. "Save config" writes the user's
  csolrc (`~/.config/csol`, `%APPDATA%\csol` on Windows), which includes
  the system one; scores and stats go to `~/.local/share/csol`
  (`%APPDATA%\csol`).
- Local static build: `docker run --rm --memory=4g -v "$PWD":/src -w /src
  alpine:3.22 sh -c "apk add build-base ncurses-dev ncurses-static && cc
  -O2 -std=c89 -Wall -pedantic -DUSE_GETOPT src/*.c -static -lncursesw -o
  out/csol"` (as root, then chown `out/`). macOS needs
  `-D_DARWIN_C_SOURCE`. Windows: MinGW against PDCurses 3.9 wincon with
  `-DUSE_PDCURSES -DUSE_GETOPT -DPDC_NCMOUSE` (see the release workflow);
  it runs under Wine, though Wine's terminal output drops the cp437 suit
  glyphs that a Windows console shows.
- Run tests and recordings under `systemd-run --user --scope -p
  MemoryMax=4G`.
- csol takes the mouse (left click picks a card, right click puts it
  down); ncurses holds a click back about 1/6 s to tell a double click, so
  scripted clicks need a gap of at least that.
- It prints "Using configuration file: <path>" before the board comes up;
  the preview script removes that line from the cast.
