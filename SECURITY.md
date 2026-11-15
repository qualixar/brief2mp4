# Security policy

brief2mp4 is a skill: instructions, bash and PowerShell scripts, and an optional Python and Node 3D pack that run on your own machine. It makes no network calls of its own at render time. The installers download only from npm, PyPI and the official package managers (Homebrew, winget, apt).

## What runs as code

Two inputs are executed, by design: a 3D pack model spec (`b2m3d model spec.py`) is Python, and a HyperFrames composition is HTML and JavaScript run in headless Chrome. Treat both like any script: only build from specs and compositions you wrote or trust. A brief itself is plain text and is never executed.

## Supported versions

Only the latest release gets fixes.

## Report a vulnerability

Please do not open a public issue. Use GitHub's private reporting: **Security > Report a vulnerability** on this repository. Include the version, your OS, and steps to reproduce. You should get a reply within seven days.

Things we treat as security issues: a script that writes or deletes outside the project folder or its own install folder, an installer that runs with elevated rights without saying so, any path that executes content from a brief, and dependency pins with known critical vulnerabilities.
