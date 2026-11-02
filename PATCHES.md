# Changes from upstream

This is the Asciiverse packaging of [csol](https://github.com/nielssp/csol)
by Niels Sonnich Poulsen (MIT), built from upstream's master as of
`b3bd193` (19 July 2025): release 1.6.0 plus the confirm dialog's mouse
support, a fix for CMake's Ninja backend (sertonix) and casing for the
default answer in confirmations. Upstream is the `upstream` remote; the
`asciiverse` branch carries the changes below.

## Code

- **csolrc is found beside the program, and settings and scores live in
  the user's folders.** csol looked for its configuration in the user's
  folder, then `/etc/xdg/csol`, then the current folder. Installed in a
  folder of its own (as av does), it only worked when started from that
  folder, and "Save config" then rewrote the csolrc there and put csolcfg
  beside it, where an update replaces them. A csolrc beside the program
  (found from the program's own path: `/proc/self/exe`,
  `_NSGetExecutablePath`, `GetModuleFileName`) now counts as the system
  one, so saving writes the user's csolrc, which includes it by its full
  path. macOS uses the XDG folders as Linux does (`~/.config/csol`,
  `~/.local/share/csol`) instead of the program's folder, and Windows
  keeps settings, scores and stats in `%APPDATA%\csol` (creating folders
  under a drive letter works now, and `_mkdir` is declared). Worth
  offering upstream.

## Building

- **macOS needs `-D_DARWIN_C_SOURCE`.** The sources define
  `_XOPEN_SOURCE 500`, under which macOS hides `strdup`; current clang then
  stops on the implicit declarations. The release workflow passes the
  flag; no code change.

## Packaging (new files)

- `.github/workflows/release.yml`: av archives for Linux (static with
  ncursesw, x86-64 and ARM64), macOS (x86-64 and ARM64) and Windows
  (x86-64, MinGW with PDCurses 3.9, upstream's own Windows setup), each
  with csolrc, games/ and themes/ beside the program; plus SHA256SUMS, and
  .deb, .rpm, .apk and Arch packages with the configuration in
  `/etc/xdg/csol` and the man page.
- `asciiverse/csolrc-windows`: upstream's `win/csolrc` with the paths for
  games/ and themes/ beside the program (cp437 theme, menu bar shown).
- `asciiverse/nfpm.yaml`: the system packages.
- `asciiverse/record-preview.py`: records the catalog preview, a game of
  FreeCell solved and played with the mouse to the victory animation.

## Ours

- **How to play it, at the top of README.md.** A short note on installing
  and starting it with av; the original text follows unchanged.
