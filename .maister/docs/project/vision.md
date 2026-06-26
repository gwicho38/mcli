# Project Vision

## Overview
mcli is a portable, version-controlled CLI framework and workflow automation tool that turns any script into a first-class command. Philosophy: **"Run first. Register later."**

## Current State
- **Age**: ~13 months (oldest commit 2025-06-09, 883+ commits).
- **Status**: Active development; weekly release cadence (currently v8.0.62).
- **Users**: Developers automating repetitive tasks across repos; internal tooling for AI/ML and trading workflows.
- **Tech Stack**: Python 3.10–3.12 + Rust extensions, Click CLI, UV, pytest, IPFS-backed workflow sync.

## Purpose
Developers accumulate one-off scripts that are hard to share, version, or rediscover. mcli solves this: drop a script into the commands directory and it becomes a discoverable, runnable, versionable command — with auto-detected language, extracted metadata, lazy-loaded dependencies, and optional IPFS sharing across machines and teams.

## Goals (Next 6–12 Months)
- Remove vestigial/orphaned code (~4.8K LOC, issue #209) to shrink surface area.
- Consolidate optional vs core dependencies (e.g., unused `anthropic`/`ollama` core declarations).
- Raise test coverage target from 30% toward 50%+; populate property-based tests.
- Expand documentation: ADRs for core patterns, workflow tutorials, API reference, config-precedence guide.
- Strengthen friendly runtime error surfaces for crashing workflow scripts (recently shipped, keep refining).

## Evolution
mcli has matured from a script runner into a layered framework with lazy command discovery, a pluggable storage layer, decentralized workflow sync, and a constants-enforced codebase. The trajectory is toward a leaner core, better-documented internals, and a smoother drag-and-drop authoring experience — while keeping startup fast and the developer loop tight.
