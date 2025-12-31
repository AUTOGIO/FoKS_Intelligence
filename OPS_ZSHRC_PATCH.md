# ~/.zshrc Patch for FBP Activation

## Safe FBP Virtual Environment Activation

Paste this block into your `~/.zshrc` file:

```bash
# ============================================================================
# FBP Backend Virtual Environment (Safe Activation)
# ============================================================================
# Only activates if venv exists, never throws errors, protects terminal
# ============================================================================

# FBP Virtual Environment Path
FBP_VENV_PATH="$HOME/.venvs/fbp"

# Conditionally activate FBP venv if it exists
if [[ -d "$FBP_VENV_PATH" ]] && [[ -f "$FBP_VENV_PATH/bin/activate" ]]; then
    # Safe activation: suppress errors, never exit terminal
    source "$FBP_VENV_PATH/bin/activate" 2>/dev/null || true
    
    # Optional: Verify activation (non-blocking)
    if [[ -n "${VIRTUAL_ENV:-}" ]] && [[ "$VIRTUAL_ENV" == "$FBP_VENV_PATH" ]]; then
        # FBP venv is active (silent success)
        :
    fi
fi

# ============================================================================
# NFA Environment Variables
# ============================================================================
# Set empty defaults (user should populate via .env or manually)
# ============================================================================

export NFA_USERNAME="${NFA_USERNAME:-}"
export NFA_PASSWORD="${NFA_PASSWORD:-}"
export NFA_EMITENTE_CNPJ="${NFA_EMITENTE_CNPJ:-}"

# ============================================================================
# End of FBP Configuration
# ============================================================================
```

## Features

✅ **Safe Activation**: Only activates if `~/.venvs/fbp` exists and has `bin/activate`  
✅ **Error Suppression**: Uses `2>/dev/null || true` to prevent terminal errors  
✅ **No Exit Calls**: Never calls `exit` or `return` that would break the shell  
✅ **Idempotent**: Safe to source multiple times  
✅ **Environment Variables**: Sets NFA credentials (empty by default)  
✅ **Non-Blocking**: Verification checks don't interrupt shell startup  

## Usage

After adding to `~/.zshrc`:

```bash
# Reload shell configuration
source ~/.zshrc

# Or open a new terminal

# Verify FBP venv is active (if it exists)
echo $VIRTUAL_ENV

# Check NFA environment variables
echo "NFA_USERNAME: ${NFA_USERNAME:-not set}"
echo "NFA_PASSWORD: ${NFA_PASSWORD:+set}"  # Shows "set" if not empty, nothing if empty
echo "NFA_EMITENTE_CNPJ: ${NFA_EMITENTE_CNPJ:-not set}"
```

## Setting NFA Credentials

To set NFA credentials, add to `~/.zshrc` AFTER the block above, or use:

```bash
# In ~/.zshrc or ~/.zshenv (more secure)
export NFA_USERNAME="your_username"
export NFA_PASSWORD="your_password"
export NFA_EMITENTE_CNPJ="your_cnpj"
```

Or use a `.env` file and source it:

```bash
# In ~/.zshrc (after the FBP block)
if [[ -f "$HOME/.env.nfa" ]]; then
    source "$HOME/.env.nfa" 2>/dev/null || true
fi
```

## Testing

Test the patch safely:

```bash
# Test activation (should not error even if venv doesn't exist)
bash -c 'source ~/.zshrc; echo "Shell loaded successfully"'

# Check if variables are set
env | grep NFA_
```
