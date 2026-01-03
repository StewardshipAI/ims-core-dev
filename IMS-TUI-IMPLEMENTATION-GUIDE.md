# IMS-TUI Implementation Guide: From Prototype to VS Code Architecture

**Target Audience:** Expert Rust Developer / LLM
**Goal:** Refactor the current `ims-tui` prototype into a robust, command-driven architecture mirroring VS Code, as specified in the "Behavioral + Systems Contract."

---

## 🏗️ Core Architectural Refactor

The current application is a monolithic `AppState` with direct event handling. The target architecture requires decoupling logic via a **Command Bus**.

### 1. The Command System (Priority #1)
**Requirement:** Implement a central command dispatcher that isolates UI events from business logic.

*   **Create `src/commands/mod.rs`:**
    ```rust
    pub struct Command {
        pub id: &'static str,
        pub title: &'static str,
        pub handler: Box<dyn Fn(&mut AppState, CommandContext) -> Result<()>>,
    }
    
    pub struct CommandRegistry {
        commands: HashMap<String, Command>,
    }
    ```
*   **Refactor Input Handlers:**
    *   Old: `KeyCode::Enter => state.open_selected_file()`
    *   New: `KeyCode::Enter => dispatcher.execute("files.open", context)`

### 2. State Management (The "State Graph")
**Requirement:** strictly separate transient UI state from persistent Workspace state.

*   **Refactor `AppState` in `src/app/state.rs`:**
    *   **`WorkspaceState`:** File tree, open files, unsaved changes (Logic).
    *   **`UiState`:** Focus, scroll offsets, window sizes (Visuals).
    *   **`AgentState`:** Conversation history, active models, token usage (Backend).
*   **Action:** Split the current giant `AppState` struct into these three composable structs.

### 3. Backend Integration (The "Prompt Loop")
**Requirement:** Connect the `Prompt Box` to the backend via the Command System.

*   **Implement Command:** `agent.submitPrompt`
*   **Logic:**
    1.  User hits Enter in Prompt Box.
    2.  UI dispatches `agent.submitPrompt` with payload `{ text: input_buffer }`.
    3.  **Command Handler:**
        *   Updates `AgentState` (adds user message).
        *   Calls `ImsApiClient::send_prompt(text)`.
        *   Spawns an async task to handle the streaming response.
        *   Updates `AgentState` with tokens as they arrive.
*   **Visuals:** The "Thinking" pane must observe `AgentState` and render updates automatically.

### 4. The Contribution System (Plugins)
**Requirement:** Allow features to register themselves without modifying core code.

*   **Create trait `Contribution`:**
    ```rust
    trait Contribution {
        fn register_commands(&self, registry: &mut CommandRegistry);
        fn sidebar_views(&self) -> Vec<SidebarItem>;
    }
    ```
*   **Implement `CoreContribution`:** Move standard file explorer and settings logic into a default contribution.

---

## 🛠️ specific Feature Requests

### A. Clipboard Integration (System Copy/Paste)
**Requirement:** Allow copying/pasting without holding Shift.
*   **Crate:** Add `arboard` (Rust clipboard crate).
*   **Logic:**
    *   `Ctrl+C`: Copy selected text (or active file path) to system clipboard.
    *   `Ctrl+V`: Paste from system clipboard into Prompt Box.

### B. File Management
**Requirement:** Full VS Code file operations.
*   **Commands:**
    *   `files.newFile`: Prompt for name -> Create node -> Select it.
    *   `files.newFolder`: Prompt for name -> Create dir node.
    *   `files.rename`: Focused node -> Toggle edit mode -> Rename on Enter.
    *   `files.delete`: Focused node -> Confirm -> Remove.

### C. Mouse Interaction
**Requirement:** Richer mouse support.
*   **Click:** Already implemented (Focus).
*   **Right Click:** Open `ContextMenu` widget at cursor position (needs new Widget).
*   **Drag:** Resize panes (requires calculating layout splitters).

---

## 📋 Step-by-Step Execution Plan

1.  **Command Bus:** Create the registry and migrate `Quit`, `ToggleSettings`, and `Focus` actions to commands.
2.  **Prompt Connection:** Implement the `ImsApiClient::chat` method and the `agent.submitPrompt` command to make the prompt box functional.
3.  **Refactor State:** Split `AppState` to clean up the code.
4.  **Clipboard:** Add `arboard` and bind `Ctrl+C`/`V`.

---

**Dependencies to Add:**
- `arboard`: For system clipboard.
- `tui-textarea`: (Optional) For better text editing in the prompt box (multi-line, cursor movement).
