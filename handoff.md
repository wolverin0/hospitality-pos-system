• Here’s a clean handoff summary you can paste into the next session.

  What we set up

  - Go 1.25.5 installed in /usr/local/go (verified with /usr/local/go/bin/go version).
  - Gastown repo cloned into /mnt/g/_OneDrive/OneDrive/Desktop/Py Apps/gastown from https://github.com/steveyegge/gastown.
  - Gas Town HQ created inside the repo at /mnt/g/_OneDrive/OneDrive/Desktop/Py Apps/gastown/gt.
  - gt installed with go install github.com/steveyegge/gastown/cmd/gt@latest (binary in ~/go/bin/gt).
  - bd (Beads CLI) installed with go install github.com/steveyegge/beads/cmd/bd@latest (binary in ~/go/bin/bd).
  - bd init run in /mnt/g/_OneDrive/OneDrive/Desktop/Py Apps/gastown/gt (creates .beads/ db).
  - PATH line added to ~/.profile: export PATH="$PATH:$HOME/go/bin" (not yet sourced).
  - Rig added: gastown pointing to /mnt/g/_OneDrive/OneDrive/Desktop/Py Apps/gastown.
  - routes.jsonl created at /mnt/g/_OneDrive/OneDrive/Desktop/Py Apps/gastown/gt/.beads/routes.jsonl with ga- and hq- prefixes.
  - Rig booted: gt rig boot gastown.

  Notes / gotchas

  - gt and bd won’t be found unless PATH is updated. Run source ~/.profile or use ~/go/bin/gt.
  - gt prime shows the Mayor context (terminal UI is text-based).
  - gt doctor reports missing patrol molecules/agent beads and orphaned claude processes. Running gt doctor --fix will kill orphaned processes.

  How to use Gas Town (basic workflow)

  - Start UI:
    cd "/mnt/g/_OneDrive/OneDrive/Desktop/Py Apps/gastown/gt"
    ~/go/bin/gt prime
  - List rigs: ~/go/bin/gt rig list
  - Create a personal workspace for the repo:
    ~/go/bin/gt crew add you --rig gastown
    cd "/mnt/g/_OneDrive/OneDrive/Desktop/Py Apps/gastown/gt/gastown/crew/you"

  If you want the next session to finish setup

  - Source PATH: source ~/.profile
  - Optional fixups (will kill orphaned claude processes): ~/go/bin/gt doctor --fix