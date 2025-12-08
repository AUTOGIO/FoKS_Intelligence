#!/usr/bin/env bash
# FoKS Intelligence Virtualenv Guard
# Ensures that when a virtual environment is active, its bin directory is
# always at the front of PATH (works for bash and zsh).

if [[ -z ${FOKS_VENV_GUARD_LOADED:-} ]]; then
  export FOKS_VENV_GUARD_LOADED=1

  _foks_fix_path() {
    if [[ -n ${VIRTUAL_ENV:-} && -d "$VIRTUAL_ENV/bin" ]]; then
      local path_with_colons=":${PATH:-}:"
      local needle=":$VIRTUAL_ENV/bin:"
      path_with_colons="${path_with_colons//$needle/:}"
      path_with_colons="${path_with_colons#:}"
      path_with_colons="${path_with_colons%:}"
      if [[ -n "$path_with_colons" ]]; then
        export PATH="$VIRTUAL_ENV/bin:$path_with_colons"
      else
        export PATH="$VIRTUAL_ENV/bin"
      fi
    fi
  }

  if [[ -n ${ZSH_VERSION:-} ]]; then
    if command -v add-zsh-hook >/dev/null 2>&1; then
      add-zsh-hook precmd _foks_fix_path 2>/dev/null || true
      add-zsh-hook preexec _foks_fix_path 2>/dev/null || true
    fi
  else
    case ":${PROMPT_COMMAND:-}:" in
      *:_foks_fix_path:*) ;;
      *) PROMPT_COMMAND="_foks_fix_path${PROMPT_COMMAND:+;$PROMPT_COMMAND}"; export PROMPT_COMMAND ;;
    esac
  fi

  _foks_fix_path
fi
