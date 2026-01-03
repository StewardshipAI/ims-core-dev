# ADR-002: Language and TUI Library Selection

**Status:** Accepted
**Date:** 2026-01-01
**Deciders:** Vibe-Coder, Honest Assistant (Scrupulous Architect)
**Technical Story:** IMS-Core Implementation - Workspace & Settings Engine

## Context and Problem Statement
We need a high-performance terminal interface that mimics a modern IDE (VS Code). The tool must handle concurrent AI agent streams, real-time file status updates (🟢/⚪), and complex, nested layouts with independent scroll behaviors.

**Drivers:**
* **Memory Safety:** Prevent crashes during long-running agent tasks using Rust's ownership model.
* **Speed:** Maintain 60FPS UI updates even while streaming thousands of tokens.
* **UX Precision:** Support "Smart Scrolling" (auto-scroll vs. manual override) and vendor-specific branding (cursors/logos).

## Decision Drivers
* **Concurrency:** Handling background agent work without freezing the UI.
* **Extensibility:** The ability to add new settings and model providers without refactoring the UI engine.
* **Auditability:** Clear visual indicators of agent state across the entire file system.

## Decision Outcome
Chosen option: **Rust (Ratatui + Crossterm)**.
**Justification:** Rust’s `Tokio` ecosystem allows for robust asynchronous model orchestration, while Ratatui’s immediate-mode rendering perfectly suits a dynamic, multi-pane "Nerve Center."

### Positive Consequences
* **State-Driven Scroll Controller:** Allows independent "Sticky Scroll" logic for Thinking and Generation windows.
* **Settings Registry:** A centralized `SettingItem` list allows for low-effort feature expansion.
* **Visual Fidelity:** High-density sidebars with status lights and vendor-specific virtual cursors.

### Negative Consequences
* **Learning Curve:** Increased complexity for a first-time programmer (Ownership/Borrow Checker).
* **Boilerplate:** Requires manual management of terminal raw mode and "cleanup" on exit.
* **Virtual Cursor Limitation:** In a terminal, the "vendor logo cursor" is a character-based simulation, not a true high-res graphical cursor.
* **State Complexity:** Managing independent scroll states for multiple files requires careful ownership management in Rust.

## Links
* [Link to SPEC-TUI-INTERFACE.md]
* [Link to RFC-002-VSCODE-TUI-LAYOUT.md]