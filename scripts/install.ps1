# install.ps1

# The purpose of this script is to install pycons3rtapi into your local
# python installation

# To automate the install, execute this script like this:
# start /wait powershell -NoLogo -Noninteractive -ExecutionPolicy Bypass -File C:\path\to\install.ps1

$scriptPath = $MyInvocation.MyCommand.Path
$scriptDir = Split-Path $scriptPath
$pycons3rtapiDir = "$scriptDir\.."
cd $pycons3rtapiDir
python .\setup.py install
exit $lastexitcode
