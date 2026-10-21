# Minimal Showcase

> **Demo / archive surface — not production infrastructure.**

This repository contains a static showcase and trust/memory proof artifacts. Its classification does not make it a source of truth for production state, credentials, policy, or runtime configuration.

## Experimental work

The isolated AWS Boundary Operator experiment is tracked in [PR #1](https://github.com/jarrettdustinqq/minimal-showcase/pull/1). That PR is intentionally a draft: its stated real-model evidence gate has not been satisfied. Do not merge it, deploy it, or treat deterministic test-model results as proof of real-model behavior until the gate is explicitly reviewed and passed.

The experiment is intended to remain isolated from production/operator repositories. Keep production credentials, live infrastructure changes, and deployment configuration out of this repository unless a separately reviewed integration contract authorizes them.

For current canonical project and repository classifications, consult [Continuity](https://github.com/jarrettdustinqq/continuity).
