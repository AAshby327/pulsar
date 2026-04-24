# fzf configuration and useful functions for PowerShell
# This file is sourced when the Pulsar environment is activated

# -----------------------------------------------------------------------------
# FZF Default Options
# -----------------------------------------------------------------------------
$env:FZF_DEFAULT_OPTS = @"
--height 40%
--layout=reverse
--border
--inline-info
--color=dark
--color=fg:-1,bg:-1,hl:#5fff87,fg+:-1,bg+:-1,hl+:#ffaf5f
--color=info:#af87ff,prompt:#5fff87,pointer:#ff87d7,marker:#ff87d7,spinner:#ff87d7
"@

# Use ripgrep for fzf if available, otherwise use Get-ChildItem
if (Get-Command rg -ErrorAction SilentlyContinue) {
    $env:FZF_DEFAULT_COMMAND = 'rg --files --hidden --follow --glob "!.git/*"'
    $env:FZF_CTRL_T_COMMAND = $env:FZF_DEFAULT_COMMAND
}

# -----------------------------------------------------------------------------
# Key Bindings (PSReadLine integration)
# -----------------------------------------------------------------------------

# Check if PSReadLine is available
if (Get-Module -ListAvailable -Name PSReadLine) {
    # Import PSReadLine if not already loaded
    if (-not (Get-Module -Name PSReadLine)) {
        Import-Module PSReadLine
    }

    # Ctrl-T: Fuzzy find files
    Set-PSReadLineKeyHandler -Key 'Ctrl+t' -ScriptBlock {
        $line = $null
        $cursor = $null
        [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

        $files = if ($env:FZF_CTRL_T_COMMAND) {
            Invoke-Expression $env:FZF_CTRL_T_COMMAND
        } else {
            Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
        } | fzf -m --preview 'bat --style=numbers --color=always --line-range :500 {} 2>$null; if (!$?) { Get-Content {} }'

        if ($files) {
            $files = ($files -split "`n" | ForEach-Object { "`"$_`"" }) -join ' '
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert($files)
        }
    }

    # Ctrl-R: Fuzzy search command history
    Set-PSReadLineKeyHandler -Key 'Ctrl+r' -ScriptBlock {
        $line = $null
        $cursor = $null
        [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

        $selected = Get-Content (Get-PSReadLineOption).HistorySavePath -ErrorAction SilentlyContinue |
            Select-Object -Unique |
            fzf --tiebreak=index --query $line

        if ($selected) {
            [Microsoft.PowerShell.PSConsoleReadLine]::RevertLine()
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert($selected)
        }
    }
}

# -----------------------------------------------------------------------------
# Useful Functions
# -----------------------------------------------------------------------------

# fcd - Fuzzy change directory
function fcd {
    param([string]$Path = ".")

    $dir = Get-ChildItem -Path $Path -Recurse -Directory -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName |
        fzf --preview 'Get-ChildItem {} | Format-Table -AutoSize | Out-String' +m

    if ($dir) {
        Set-Location $dir
    }
}

# fopen - Fuzzy find and open file with default editor
function fopen {
    param([string]$Query = "")

    $files = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName |
        fzf --query=$Query --multi --select-1 --exit-0 --preview 'bat --style=numbers --color=always --line-range :500 {} 2>$null; if (!$?) { Get-Content {} }'

    if ($files) {
        $editor = if ($env:EDITOR) { $env:EDITOR } else { "notepad" }
        $files -split "`n" | ForEach-Object {
            & $editor $_
        }
    }
}

# fkill - Fuzzy find and kill process
function fkill {
    param([int]$Signal = 9)

    $processes = Get-Process |
        Select-Object Id, ProcessName, CPU, WorkingSet |
        Sort-Object CPU -Descending |
        Format-Table -AutoSize |
        Out-String -Stream |
        fzf -m --header-lines=3

    if ($processes) {
        $processes | ForEach-Object {
            if ($_ -match '^\s*(\d+)') {
                $pid = $matches[1]
                Write-Host "Stopping process $pid..."
                Stop-Process -Id $pid -Force
            }
        }
    }
}

# fgit - Fuzzy git branch checkout
function fgit {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "Git is not installed" -ForegroundColor Red
        return
    }

    $branch = git branch -a |
        ForEach-Object { $_.Trim() -replace '^\*\s+', '' } |
        fzf +m --preview 'git log --oneline --graph --color=always {}'

    if ($branch) {
        $branch = $branch -replace 'remotes/[^/]+/', ''
        git checkout $branch
    }
}

# fglog - Fuzzy git log browser
function fglog {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "Git is not installed" -ForegroundColor Red
        return
    }

    $commit = git log --graph --color=always --format="%C(auto)%h%d %s %C(black)%C(bold)%cr" |
        fzf --ansi --no-sort --reverse --tiebreak=index --preview 'git show --color=always {1}' |
        ForEach-Object { if ($_ -match '\b([a-f0-9]{7})\b') { $matches[1] } }

    if ($commit) {
        git show --color=always $commit | less -R
    }
}

# frg - Fuzzy ripgrep search
function frg {
    param([string]$Pattern = "")

    if (-not (Get-Command rg -ErrorAction SilentlyContinue)) {
        Write-Host "ripgrep is not installed. Please install it for better performance." -ForegroundColor Red
        return
    }

    $selected = rg --color=always --line-number --no-heading --smart-case $Pattern |
        fzf --ansi --color "hl:-1:underline,hl+:-1:underline:reverse" --delimiter ':' --preview 'bat --color=always {1} --highlight-line {2} 2>$null; if (!$?) { Get-Content {1} }'

    if ($selected) {
        if ($selected -match '^([^:]+):(\d+)') {
            $file = $matches[1]
            $line = $matches[2]
            $editor = if ($env:EDITOR) { $env:EDITOR } else { "notepad" }
            & $editor $file
        }
    }
}

# fenv - Fuzzy search environment variables
function fenv {
    $var = Get-ChildItem Env: |
        ForEach-Object { "$($_.Name)=$($_.Value)" } |
        fzf --preview 'echo {}' |
        ForEach-Object { if ($_ -match '^([^=]+)=') { $matches[1] } }

    if ($var) {
        Get-Item "Env:$var" | Select-Object Name, Value
    }
}

# falias - Fuzzy search aliases
function falias {
    $alias = Get-Alias |
        ForEach-Object { "$($_.Name) -> $($_.Definition)" } |
        fzf --preview 'echo {}' |
        ForEach-Object { if ($_ -match '^([^\s]+)') { $matches[1] } }

    if ($alias) {
        Get-Alias $alias
    }
}

# fcmd - Fuzzy search available commands
function fcmd {
    $cmd = Get-Command |
        Select-Object -ExpandProperty Name |
        Sort-Object -Unique |
        fzf --preview 'Get-Command {} | Format-List | Out-String'

    if ($cmd) {
        Get-Command $cmd | Format-List
    }
}

# fhist - Fuzzy search PowerShell history
function fhist {
    $historyPath = (Get-PSReadLineOption).HistorySavePath
    if (Test-Path $historyPath) {
        $cmd = Get-Content $historyPath |
            Select-Object -Unique |
            fzf --tiebreak=index --preview 'echo {}'

        if ($cmd) {
            Set-Clipboard $cmd
            Write-Host "Command copied to clipboard: $cmd" -ForegroundColor Green
        }
    }
}

# fpath - Fuzzy search PATH directories
function fpath {
    $dir = $env:PATH -split ';' |
        Where-Object { $_ -and (Test-Path $_) } |
        fzf --preview 'Get-ChildItem {} | Format-Table -AutoSize | Out-String'

    if ($dir) {
        Set-Location $dir
    }
}

# -----------------------------------------------------------------------------
# Aliases
# -----------------------------------------------------------------------------
Set-Alias -Name ff -Value fzf -ErrorAction SilentlyContinue
Set-Alias -Name ffd -Value fcd -ErrorAction SilentlyContinue
Set-Alias -Name ffg -Value frg -ErrorAction SilentlyContinue
Set-Alias -Name ffo -Value fopen -ErrorAction SilentlyContinue
Set-Alias -Name ffk -Value fkill -ErrorAction SilentlyContinue

Write-Host "fzf functions loaded: fcd, fopen, fkill, fgit, fglog, frg, fenv, falias, fcmd, fhist, fpath" -ForegroundColor Green
