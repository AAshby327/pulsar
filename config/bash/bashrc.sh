
# aliases
alias lsa="ls -a"
alias lt="ls --human-readable --size -1 --classify"
alias ..="cd .."
alias ...="cd ../.."
alias ....="cd ../../.."

alias c="clear"
alias h="history"

mkcd() {
    mkdir -p "$1" && cd "$1"
}