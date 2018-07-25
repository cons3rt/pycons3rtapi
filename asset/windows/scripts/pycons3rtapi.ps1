# pycons3rtapi.ps1

$ErrorActionPreference = "Stop"
#$scriptPath = Split-Path -LiteralPath $(if ($PSVersionTable.PSVersion.Major -ge 3) { $PSCommandPath } else { & { $MyInvocation.ScriptName } })
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# Load the PATH environment variable
$env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine")

########################### VARIABLES ###############################

$ASSET_DIR = "$env:ASSET_DIR"
$TIMESTAMP = Get-Date -f yyyy-MM-dd-HHmm

# exit code
$exitCode = 0

# Log files
$LOGTAG = "pycons3rtapi-install"
$LOGFILE = "C:\log\$LOGTAG-$TIMESTAMP.log"

# Deployment properties file
$propFile="$env:DEPLOYMENT_HOME/deployment.properties"

# Root directory for pycons3rt
$pycons3rtRootDir = "C:\pycons3rt"
$sourceDir = "$pycons3rtRootDir/src/pycons3rtapi"

# Git clone URL
$gitUrl = "https://github.com/cons3rt/pycons3rtapi.git"

# Default branch to clone
$defaultBranch = "master"

######################### END VARIABLES #############################

######################## HELPER FUNCTIONS ############################

# Set up logging functions
function logger($level, $logstring) {
   $stamp = get-date -f yyyyMMdd-HHmmss
   $logmsg = "$stamp - $LOGTAG - [$level] - $logstring"
   write-output $logmsg
}
function logErr($logstring) { logger "ERROR" $logstring }
function logWarn($logstring) { logger "WARNING" $logstring }
function logInfo($logstring) { logger "INFO" $logstring }

###################### END HELPER FUNCTIONS ##########################

######################## SCRIPT EXECUTION ############################

new-item $logfile -itemType file -force
start-transcript -append -path $logfile
logInfo "Running $LOGTAG..."

try {
	logInfo "Installing $LOGTAG at: $TIMESTAMP"

	if ( test-path $propFile ) {
        logInfo "Found deployment properties file: $propFile"

        # Get the branch from the deployment.properties file
        $branch = Get-Content $propFile | Select-String PYCONS3RTAPI_BRANCH | foreach {$d = $_ -split "="; Write-Output $d[1] }

        if ( ! $branch ) {
            logInfo "PYCONS3RTAPI_BRANCH deployment property not found in deployment properties, using default branch: $defaultBranch"
            $branch = $defaultBranch
        }
        else {
            logInfo "Found PYCONS3RTAPI_BRANCH set to: $branch"
        }
    }
    else {
        logInfo "Deployment properties file not found, using default branch: $defaultBranch"
        $branch = $defaultBranch
    }

    logInfo "Creating directory: $sourceDir..."
    mkdir $sourceDir

    # Clone the pycons3rtapi source
    logInfo "Cloning pycons3rtapi source code..."
    git clone -b $branch $gitUrl $sourceDir

    # Ensure the install script was found
    if ( test-path $sourceDir\scripts\install.ps1 ) {
        logInfo "Found the pycons3rtapi install script"
    }
    else {
        $errMsg="pycons3rtapi install script not found, git clone may not have succeeded: $sourceDir\scripts\install.ps1"
        logErr $errMsg
        throw $errMsg
    }

    # Install PIP prerequisites
    pip install requests_toolbelt

    # Run the pycons3rtapi setup
    logInfo "Installing pycons3rtapi..."
    cd $sourceDir
    powershell -NoLogo -Noninteractive -ExecutionPolicy Bypass -File .\scripts\install.ps1
    $result = $lastexitcode

    if ( $result -ne 0 ) {
        $errMsg="There was a problem setting up pycons3rtapi"
        logErr $errMsg
        throw $errMsg
    }
}
catch {
    logErr "Caught exception: $_"
    $exitCode = 1
}
finally {
    logInfo "$LOGTAG complete in $($stopwatch.Elapsed)"
}

###################### END SCRIPT EXECUTION ##########################

logInfo "Exiting with code: $exitCode"
stop-transcript
get-content -Path $logfile
exit $exitCode
