
# PowerShell aliases

# Directory listing aliases
Set-Alias -Name lsa -Value Get-ChildItem -Option AllScope
function Get-ChildItemAll { Get-ChildItem -Force }
Set-Alias -Name lsa -Value Get-ChildItemAll -Force

function Get-ChildItemSorted {
    Get-ChildItem | Sort-Object Length | Format-Table Mode, Length, Name -AutoSize
}
Set-Alias -Name lt -Value Get-ChildItemSorted

# Navigation aliases
function cd.. { Set-Location .. }
function cd... { Set-Location ../.. }
function cd.... { Set-Location ../../.. }
Set-Alias -Name .. -Value cd..
Set-Alias -Name ... -Value cd...
Set-Alias -Name .... -Value cd....

# Utility aliases
Set-Alias -Name c -Value Clear-Host
Set-Alias -Name h -Value Get-History

# mkcd function - create directory and navigate into it
function mkcd {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path
    )
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    Set-Location $Path
}
