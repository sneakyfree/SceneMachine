# Remove ELECTRON_RUN_AS_NODE to allow Electron to run properly
if (Test-Path Env:ELECTRON_RUN_AS_NODE) {
    Remove-Item Env:ELECTRON_RUN_AS_NODE
}

# Set development environment
$env:NODE_ENV = "development"

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$electronPath = Join-Path $scriptDir "..\..\node_modules\electron\dist\electron.exe"
$appPath = $scriptDir

# Start Electron
& $electronPath $appPath
