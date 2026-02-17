# Thinking Diagnostic — Design Spec (v0.1)

This folder contains the design specification for the Thinking Diagnostic:
questions, scoring rules, feedback text, modules, and resources.

These files are NOT used by the live Django site yet.
They are safe to edit and exist only for planning and versioning.

Each breakpoint has 3 scenarios.

The diagnostic shows 1 by default, and conditionally shows 2 more if the breakpoint is dominant.

Note: Choice order (A/B/C/D) is randomized at render time in the web app.
The order in YAML is semantic, not presentational.

Status: design phase
