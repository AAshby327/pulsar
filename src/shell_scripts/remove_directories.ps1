param(
    [Parameter(Mandatory=$true, ValueFromRemainingArguments=$true)]
    [string[]]$TargetPaths
)

$ErrorActionPreference = "Stop"

# Validate that PULSAR_ROOT is set
if (-not $env:PULSAR_ROOT) {
    Write-Error "PULSAR_ROOT environment variable is not set"
    exit 1
}

$pulsarRoot = [System.IO.Path]::GetFullPath($env:PULSAR_ROOT)

# Resolve and validate all target paths
$resolvedPaths = @()
foreach ($targetPath in $TargetPaths) {
    $targetPathResolved = [System.IO.Path]::GetFullPath($targetPath)

    # Ensure target path is within PULSAR_ROOT
    if (-not $targetPathResolved.StartsWith($pulsarRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Write-Error "Target path '$targetPathResolved' is not within PULSAR_ROOT '$pulsarRoot'"
        exit 1
    }

    $resolvedPaths += $targetPathResolved
}

# Function to check if a path is protected (src or config directories, unless it's __pycache__)
function Test-IsProtectedPath {
    param([string]$Path)

    $relativePath = $Path.Substring($pulsarRoot.Length).TrimStart('\', '/')
    $parts = $relativePath -split '[/\\]'

    # If it's a __pycache__ directory anywhere, it's NOT protected
    if ($parts -contains '__pycache__') {
        return $false
    }

    # If the first part is 'src' or 'config', it's protected
    if ($parts.Length -gt 0 -and ($parts[0] -eq 'src' -or $parts[0] -eq 'config')) {
        return $true
    }

    return $false
}

# Validate all paths and check if they're protected
foreach ($targetPathResolved in $resolvedPaths) {
    # Check if the target path itself is protected
    if (Test-IsProtectedPath -Path $targetPathResolved) {
        Write-Error "Cannot delete protected directory: $targetPathResolved (src and config directories are protected)"
        exit 1
    }

    # Exit if directory doesn't exist
    if (-not (Test-Path -Path $targetPathResolved -PathType Container)) {
        Write-Host "Directory does not exist: $targetPathResolved"
        continue
    }
}

# Find all executable and binary files across all directories
$executableExtensions = @('.exe', '.dll', '.pyd', '.so')
$allExecutableFiles = @()

foreach ($targetPathResolved in $resolvedPaths) {
    if (Test-Path -Path $targetPathResolved -PathType Container) {
        $executableFiles = Get-ChildItem -Path $targetPathResolved -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $executableExtensions -contains $_.Extension }
        $allExecutableFiles += $executableFiles
    }
}

# Kill processes running from these executables
foreach ($file in $allExecutableFiles) {
    try {
        $processes = Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -and $_.Path.StartsWith($file.FullName, [StringComparison]::OrdinalIgnoreCase) }

        foreach ($proc in $processes) {
            Write-Host "Killing process: $($proc.ProcessName) (PID: $($proc.Id))"
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    } catch {
        # Continue even if we can't kill a process
        Write-Warning "Could not kill processes for: $($file.FullName)"
    }
}

# Give processes a moment to terminate
Start-Sleep -Milliseconds 500

# Function to remove read-only attributes and DENY permissions
function Remove-FileSystemRestrictions {
    param([string]$Path)

    try {
        # Remove read-only attributes
        Get-ChildItem -Path $Path -Recurse -Force -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($_.Attributes -band [System.IO.FileAttributes]::ReadOnly) {
                    $_.Attributes = $_.Attributes -bxor [System.IO.FileAttributes]::ReadOnly
                }
            }

        # Remove DENY permissions
        icacls $Path /remove:d Everyone /T /C /Q 2>&1 | Out-Null
    } catch {
        # Best effort - continue even if this fails
    }
}

# Process each directory
foreach ($targetPathResolved in $resolvedPaths) {
    # Skip if directory doesn't exist
    if (-not (Test-Path -Path $targetPathResolved -PathType Container)) {
        continue
    }

    # Remove restrictions
    Remove-FileSystemRestrictions -Path $targetPathResolved

    # Attempt to delete the directory with retries
    $maxRetries = 3
    $retryCount = 0
    $deleted = $false

    while (-not $deleted -and $retryCount -lt $maxRetries) {
        try {
            # Recursively delete, protecting src and config directories
            Get-ChildItem -Path $targetPathResolved -Recurse -Force -ErrorAction Stop |
                Sort-Object -Property FullName -Descending |
                ForEach-Object {
                    if (-not (Test-IsProtectedPath -Path $_.FullName)) {
                        Remove-Item -Path $_.FullName -Force -Recurse -ErrorAction Stop
                    }
                }

            # Remove the root directory itself if not protected
            if (-not (Test-IsProtectedPath -Path $targetPathResolved)) {
                Remove-Item -Path $targetPathResolved -Force -ErrorAction Stop
            }

            $deleted = $true
            Write-Host "Successfully deleted: $targetPathResolved"
        } catch {
            $retryCount++
            if ($retryCount -lt $maxRetries) {
                Write-Warning "Deletion attempt $retryCount failed for $targetPathResolved, retrying..."
                Start-Sleep -Milliseconds 500
            } else {
                Write-Error "Failed to delete directory after $maxRetries attempts: $targetPathResolved - $_"
                exit 1
            }
        }
    }
}
