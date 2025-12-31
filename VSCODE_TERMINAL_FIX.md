# VS Code Terminal Launch Fix

## Problem
Terminal process `/bin/bash '-l'` terminated with exit codes 127 or 1.

## Root Cause
VS Code is trying to launch bash as a login shell (`-l` flag), which may be:
1. Sourcing `.bash_profile` with errors
2. Missing dependencies in VS Code's environment
3. Misconfigured terminal profile

## Solutions Applied

### ✅ Solution 1: VS Code Settings (Applied)

Created `.vscode/settings.json` with:
- Default shell set to `zsh` (your system default)
- Bash profile without login flag
- Environment inheritance enabled

### ✅ Solution 2: Workspace Settings (Applied)

Updated `FoKS_Intelligence.code-workspace` with terminal configuration.

## Manual Fixes (If Needed)

### Option A: Use zsh Instead of bash

1. Open VS Code Settings (⌘,)
2. Search for: `terminal.integrated.defaultProfile.osx`
3. Set to: `zsh`
4. Reload VS Code

### Option B: Fix bash Profile

If you need bash, check your `~/.bash_profile`:

```bash
# Test if bash_profile has errors
bash -l -c "echo 'Test successful'"

# If it fails, check for:
# - Missing commands (exit code 127 = command not found)
# - Exit statements that terminate the shell
# - Syntax errors
```

### Option C: Use Non-Login Bash

In VS Code settings, change bash profile to:
```json
"bash": {
  "path": "/bin/bash",
  "args": []  // Remove "-l" to avoid login shell
}
```

## Verification

After applying fixes:

1. **Close all VS Code terminals**
2. **Reload VS Code** (⌘⇧P → "Reload Window")
3. **Open new terminal** (⌘` or Terminal → New Terminal)
4. **Verify shell**: `echo $SHELL` should show `/bin/zsh`

## If Still Failing

1. **Enable trace logging** in VS Code:
   - Open Command Palette (⌘⇧P)
   - Run: "Preferences: Open User Settings (JSON)"
   - Add: `"terminal.integrated.trace": true`
   - Try opening terminal
   - Check Output panel → "Terminal" for errors

2. **Check VS Code version**:
   - Help → About Visual Studio Code
   - Update if not latest

3. **Test shell directly**:
   ```bash
   /bin/bash -l -c "echo 'Test'"
   /bin/zsh -c "echo 'Test'"
   ```

## References

- [VS Code Terminal Troubleshooting](https://code.visualstudio.com/docs/supporting/troubleshoot-terminal-launch)
- Exit code 127 = Command not found
- Exit code 1 = General error

---

**Status:** ✅ Settings files created  
**Next Step:** Reload VS Code and test terminal
