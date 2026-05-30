# WSL Agent Guidelines for Antigravity

This document defines critical operational rules and conventions for any Antigravity Agent interacting with this project. Because the Antigravity host application runs on Windows while the project workspace and execution environment reside inside WSL Ubuntu, strict adherence to these rules is mandatory to prevent execution errors, path mismatches, and shell confusion.

---

## 1. System Architecture & Environment

- **Host OS (Antigravity 2.0):** Windows 11
- **Target OS (Workspace):** WSL Ubuntu (Distribution Name: `Ubuntu`)
- **Workspace Windows Path (for file I/O):** `\\wsl.localhost\Ubuntu\home\hieu0606sunny\price2026wsl\tech2ai`
- **Workspace Linux Path (for command execution):** `/home/hieu0606sunny/price2026wsl/tech2ai`
- **Python Virtual Environment:** Located inside the workspace at `/home/hieu0606sunny/price2026wsl/tech2ai/.venv` (managed by `uv`).

---

## 2. Command Execution Rules (WSL vs Windows)

### Critical Rule: Never Execute Direct Windows Commands on the Workspace
The workspace is physically located on the Linux filesystem. Attempting to run Windows commands (PowerShell or CMD) directly inside the network path `\\wsl.localhost\...` will fail, corrupt files, or cause permission errors.

### The Standard Command Wrapper Pattern
All commands (scripts, package installations, tests, and servers) must be wrapped and executed inside WSL Ubuntu.

Use the following syntax in the Windows terminal to execute commands inside the correct Linux workspace and virtual environment:

```powershell
wsl -d Ubuntu -e bash -c "cd /home/hieu0606sunny/price2026wsl/tech2ai && [YOUR_COMMAND]"
```

---

## 3. Python Execution Guidelines

Always use the local virtual environment `.venv` located in the project root to run Python scripts. Do not call global system Python.

### Running Gradio Applications
To run the main search or autonomous scanning tools, wrap the execution precisely using the local `.venv`:

#### 1. Running Multi-Source Deal Finder (search_key.py)
```powershell
wsl -d Ubuntu -e bash -c "cd /home/hieu0606sunny/price2026wsl/tech2ai && .venv/bin/python segment4/search_key.py"
```

#### 2. Running Autonomous Deal Hunter (price_is_right.py)
```powershell
wsl -d Ubuntu -e bash -c "cd /home/hieu0606sunny/price2026wsl/tech2ai && .venv/bin/python segment4/price_is_right.py"
```

### Running General Python Scripts or Package Syncs
If you need to execute general python one-liners or synchronize dependencies using `uv`:
```powershell
wsl -d Ubuntu -e bash -c "cd /home/hieu0606sunny/price2026wsl/tech2ai && .venv/bin/uv sync"
```

---

## 4. File Path Translation Rules

Antigravity Agents must distinguish between **File Operations** (reading, writing, editing) and **Process Execution** (running commands).

### For File Operations (view_file, write_to_file, replace_file_content)
Always use the Windows networking path. The agent's file utility tools run on the Windows host and access the workspace via SMB mount.
- **Correct Path:** `\\wsl.localhost\Ubuntu\home\hieu0606sunny\price2026wsl\tech2ai\<folder_name>\<file_name>`
- **Incorrect Path:** `/home/hieu0606sunny/price2026wsl/tech2ai/...`

### For Command Execution (run_command)
Always use the Linux absolute path inside the WSL wrapper. The command is executed inside the Ubuntu kernel.
- **Correct Path:** `/home/hieu0606sunny/price2026wsl/tech2ai/...`
- **Incorrect Path:** `\\wsl.localhost\Ubuntu\...`

---

## 5. Agent Verification Checklist

Before proposing or executing any command:
1. **Is the command wrapped?** Ensure it starts with `wsl -d Ubuntu -e bash -c "..."`.
2. **Is the directory correct?** Ensure it changes directory to `/home/hieu0606sunny/price2026wsl/tech2ai` first.
3. **Is the environment correct?** Ensure it calls `.venv/bin/python` or local `uv` executable, rather than system python.
4. **Is the file path correct for the tool?** Double-check if the tool uses Windows network mount paths (for file access) or Linux local paths (for terminal execution).
