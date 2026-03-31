#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Installs Windows Package Manager (winget) on Windows systems.
.DESCRIPTION
    This script downloads and installs the latest version of winget from GitHub,
    including required dependencies.
#>

$ErrorActionPreference = "Stop"

Write-Host "Checking for winget installation..." -ForegroundColor Cyan

# Check if winget is already installed
try {
    $wingetVersion = winget --version
    Write-Host "winget is already installed: $wingetVersion" -ForegroundColor Green
    $response = Read-Host "Do you want to reinstall/update? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Installation cancelled." -ForegroundColor Yellow
        exit 0
    }
} catch {
    Write-Host "winget is not installed. Proceeding with installation..." -ForegroundColor Yellow
}

Write-Host "`nInstalling winget and dependencies..." -ForegroundColor Cyan

# Create temp directory
$tempDir = Join-Path $env:TEMP "winget-install"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

try {
    # Install VCLibs dependency
    Write-Host "Downloading Microsoft VCLibs..." -ForegroundColor Yellow
    $vcLibsUrl = "https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx"
    $vcLibsPath = Join-Path $tempDir "Microsoft.VCLibs.x64.14.00.Desktop.appx"
    Invoke-WebRequest -Uri $vcLibsUrl -OutFile $vcLibsPath
    Write-Host "Installing VCLibs..." -ForegroundColor Yellow
    Add-AppxPackage -Path $vcLibsPath -ErrorAction SilentlyContinue

    # Install UI.Xaml dependency
    Write-Host "Downloading Microsoft UI.Xaml..." -ForegroundColor Yellow
    $uiXamlUrl = "https://github.com/microsoft/microsoft-ui-xaml/releases/download/v2.8.6/Microsoft.UI.Xaml.2.8.x64.appx"
    $uiXamlPath = Join-Path $tempDir "Microsoft.UI.Xaml.2.8.x64.appx"
    Invoke-WebRequest -Uri $uiXamlUrl -OutFile $uiXamlPath
    Write-Host "Installing UI.Xaml..." -ForegroundColor Yellow
    Add-AppxPackage -Path $uiXamlPath -ErrorAction SilentlyContinue

    # Get latest winget release
    Write-Host "Fetching latest winget release..." -ForegroundColor Yellow
    $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/microsoft/winget-cli/releases/latest"
    $wingetAsset = $releases.assets | Where-Object { $_.name -match "\.msixbundle$" } | Select-Object -First 1

    if (-not $wingetAsset) {
        throw "Could not find winget installer in latest release"
    }

    # Download winget
    Write-Host "Downloading winget $($releases.tag_name)..." -ForegroundColor Yellow
    $wingetPath = Join-Path $tempDir $wingetAsset.name
    Invoke-WebRequest -Uri $wingetAsset.browser_download_url -OutFile $wingetPath

    # Install winget
    Write-Host "Installing winget..." -ForegroundColor Yellow
    Add-AppxPackage -Path $wingetPath

    # Verify installation
    Write-Host "`nVerifying installation..." -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    $newVersion = winget --version
    Write-Host "Successfully installed winget: $newVersion" -ForegroundColor Green

} catch {
    Write-Host "`nError during installation: $_" -ForegroundColor Red
    exit 1
} finally {
    # Cleanup
    Write-Host "`nCleaning up temporary files..." -ForegroundColor Cyan
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "`nInstallation complete! You may need to restart your terminal." -ForegroundColor Green
