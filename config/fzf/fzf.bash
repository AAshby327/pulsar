# fzf configuration and useful functions for bash
# This file is sourced when the Pulsar environment is activated

# -----------------------------------------------------------------------------
# FZF Default Options
# -----------------------------------------------------------------------------
export FZF_DEFAULT_OPTS="
  --height 40%
  --layout=reverse
  --border
  --inline-info
  --color=dark
  --color=fg:-1,bg:-1,hl:#5fff87,fg+:-1,bg+:-1,hl+:#ffaf5f
  --color=info:#af87ff,prompt:#5fff87,pointer:#ff87d7,marker:#ff87d7,spinner:#ff87d7
"

# Use ripgrep for fzf if available, otherwise use find
if command -v rg &> /dev/null; then
  export FZF_DEFAULT_COMMAND='rg --files --hidden --follow --glob "!.git/*"'
  export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
fi

# -----------------------------------------------------------------------------
# Key Bindings (only in interactive shells)
# -----------------------------------------------------------------------------

if [[ $- == *i* ]]; then
  # CTRL-T - Paste the selected file path into the command line
  __fzf_select_file() {
    local cmd="${FZF_CTRL_T_COMMAND:-"command find -L . -mindepth 1 \\( -path '*/\\.*' -o -fstype 'sysfs' -o -fstype 'devfs' -o -fstype 'devtmpfs' -o -fstype 'proc' \\) -prune \
      -o -type f -print \
      -o -type d -print \
      -o -type l -print 2> /dev/null | cut -b3-"}"
    eval "$cmd" | fzf -m --preview 'if [ -f {} ]; then bat --style=numbers --color=always --line-range :500 {} 2>/dev/null || cat {}; else ls -la {}; fi' | while read -r item; do
      printf '%q ' "$item"
    done
    echo
  }

  bind -m emacs-standard -x '"\C-t": __fzf_select_file'
  bind -m vi-command -x '"\C-t": __fzf_select_file'
  bind -m vi-insert -x '"\C-t": __fzf_select_file'

  # CTRL-R - Search command history
  __fzf_history() {
    local output
    output=$(
      builtin fc -lnr -2147483648 |
        last_hist=$(HISTTIMEFORMAT='' builtin history 1) perl -n -l0 -e 'BEGIN { getc; $/ = "\n\t"; $HISTCMD = $ENV{last_hist} + 1 } s/^[ *]//; print $HISTCMD - $. . "\t$_" if !$seen{$_}++' |
        fzf --read0 --print0 --tiebreak=index --toggle-sort=ctrl-r --query "${READLINE_LINE}" --preview 'echo {}' --preview-window down:3:wrap |
        perl -pe 's/^\d+\t//'
    )
    READLINE_LINE="$output"
    READLINE_POINT=${#READLINE_LINE}
  }

  bind -m emacs-standard -x '"\C-r": __fzf_history'
  bind -m vi-command -x '"\C-r": __fzf_history'
  bind -m vi-insert -x '"\C-r": __fzf_history'
fi

# -----------------------------------------------------------------------------
# Useful Functions and Aliases
# -----------------------------------------------------------------------------

# fcd - Fuzzy change directory
fcd() {
  local dir
  dir=$(find ${1:-.} -type d 2> /dev/null | fzf --preview 'ls -la {}' +m) && cd "$dir"
}

# fopen - Fuzzy find and open file with default editor
fopen() {
  local files
  IFS=$'\n' files=($(fzf --query="$1" --multi --select-1 --exit-0 --preview 'bat --style=numbers --color=always --line-range :500 {} 2>/dev/null || cat {}'))
  [[ -n "$files" ]] && ${EDITOR:-vim} "${files[@]}"
}

# fkill - Fuzzy find and kill process
fkill() {
  local pid
  if [ "$UID" != "0" ]; then
    pid=$(ps -f -u $UID | sed 1d | fzf -m --preview 'echo {}' | awk '{print $2}')
  else
    pid=$(ps -ef | sed 1d | fzf -m --preview 'echo {}' | awk '{print $2}')
  fi

  if [ "x$pid" != "x" ]; then
    echo "$pid" | xargs kill -${1:-9}
  fi
}

# fgit - Fuzzy git branch checkout
fgit() {
  local branches branch
  branches=$(git branch -a) &&
  branch=$(echo "$branches" | fzf +m --preview 'git log --oneline --graph --color=always {}') &&
  git checkout $(echo "$branch" | sed "s/.* //" | sed "s#remotes/[^/]*/##")
}

# fglog - Fuzzy git log browser
fglog() {
  git log --graph --color=always \
    --format="%C(auto)%h%d %s %C(black)%C(bold)%cr" "$@" |
  fzf --ansi --no-sort --reverse --tiebreak=index --bind=ctrl-s:toggle-sort \
    --preview 'echo {} | grep -o "[a-f0-9]\{7\}" | head -1 | xargs -I % git show --color=always %' \
    --bind "enter:execute:
      (echo {} | grep -o '[a-f0-9]\{7\}' | head -1 |
      xargs -I % sh -c 'git show --color=always % | less -R') << 'FZF-EOF'
      {}
FZF-EOF"
}

# frg - Fuzzy ripgrep search
frg() {
  if ! command -v rg &> /dev/null; then
    echo "ripgrep is not installed. Please install it for better performance."
    return 1
  fi

  local selected
  selected=$(
    rg --color=always --line-number --no-heading --smart-case "${*:-}" |
      fzf --ansi \
          --color "hl:-1:underline,hl+:-1:underline:reverse" \
          --delimiter : \
          --preview 'bat --color=always {1} --highlight-line {2}' \
          --preview-window 'up,60%,border-bottom,+{2}+3/3,~3'
  )

  if [ -n "$selected" ]; then
    local file=$(echo "$selected" | cut -d: -f1)
    local line=$(echo "$selected" | cut -d: -f2)
    ${EDITOR:-vim} "$file" "+$line"
  fi
}

# fenv - Fuzzy search environment variables
fenv() {
  local var
  var=$(env | fzf --preview 'echo {}' | cut -d= -f1)
  [ -n "$var" ] && echo "${!var}"
}

# falias - Fuzzy search aliases
falias() {
  local alias_cmd
  alias_cmd=$(alias | fzf --preview 'echo {}' | cut -d= -f1)
  [ -n "$alias_cmd" ] && eval "$alias_cmd"
}

# fman - Fuzzy search man pages
fman() {
  man -k . | fzf --preview 'echo {} | cut -d" " -f1 | xargs man' | cut -d" " -f1 | xargs man
}

# -----------------------------------------------------------------------------
# Aliases
# -----------------------------------------------------------------------------
alias ff='fzf --preview "bat --style=numbers --color=always --line-range :500 {}"'
alias ffd='fcd'
alias ffg='frg'
alias ffo='fopen'
alias ffk='fkill'
