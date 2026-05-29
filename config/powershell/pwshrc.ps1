
# PowerShell aliases

# Directory listing aliases
function global:Get-ChildItemAll { Get-ChildItem -Force }
Set-Alias -Name lsa -Value Get-ChildItemAll -Scope Global

function global:Get-ChildItemSorted {
    Get-ChildItem | Sort-Object Length | Format-Table Mode, Length, Name -AutoSize
}
Set-Alias -Name lt -Value Get-ChildItemSorted -Scope Global

# Navigation aliases
function global:cd.. { Set-Location .. }
function global:cd... { Set-Location ../.. }
function global:cd.... { Set-Location ../../.. }
Set-Alias -Name .. -Value cd.. -Scope Global
Set-Alias -Name ... -Value cd... -Scope Global
Set-Alias -Name .... -Value cd.... -Scope Global

# Utility aliases
Set-Alias -Name c -Value Clear-Host -Scope Global
# Note: 'h' is already a built-in alias for Get-History

# mkcd function - create directory and navigate into it
function global:mkcd {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path
    )
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    Set-Location $Path
}
