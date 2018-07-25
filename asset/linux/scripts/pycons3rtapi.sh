#!/bin/bash

# Source the environment
if [ -f /etc/bashrc ] ; then
    . /etc/bashrc
fi
if [ -f /etc/profile ] ; then
    . /etc/profile
fi

# Establish a log file and log tag
logTag="pycons3rtapi-install"
logDir="/var/log/cons3rt"
logFile="${logDir}/${logTag}-$(date "+%Y%m%d-%H%M%S").log"

######################### GLOBAL VARIABLES #########################

# Git Server Domain Name
gitServerDomainName="github.com"

# pycons3rtapi GIT clone URL
pycons3rtapiGitUrl="https://${gitServerDomainName}/cons3rt/pycons3rtapi.git"

# Default GIT branch
defaultGitBranch="master"

# Source code directories
pycons3rtSourceDir=
sourceDir=

# Path to the pycons3rtapi linux install script
pycons3rtapiInstaller=

# Environment variable file
pycons3rtEnv="/etc/profile.d/pycons3rt.sh"

# Python info
pythonHome=
pythonExe=
pipExe=

####################### END GLOBAL VARIABLES #######################

# Logging functions
function timestamp() { date "+%F %T"; }
function logInfo() { echo -e "$(timestamp) ${logTag} [INFO]: ${1}" >> ${logFile}; }
function logWarn() { echo -e "$(timestamp) ${logTag} [WARN]: ${1}" >> ${logFile}; }
function logErr() { echo -e "$(timestamp) ${logTag} [ERROR]: ${1}" >> ${logFile}; }

function set_deployment_home() {
    # Ensure DEPLOYMENT_HOME exists
    if [ -z "${DEPLOYMENT_HOME}" ] ; then
        logWarn "DEPLOYMENT_HOME is not set, attempting to determine..."
        deploymentDirCount=$(ls /opt/cons3rt-agent/run | grep Deployment | wc -l)
        # Ensure only 1 deployment directory was found
        if [ ${deploymentDirCount} -ne 1 ] ; then
            logErr "Could not determine DEPLOYMENT_HOME"
            return 1
        fi
        # Get the full path to deployment home
        deploymentDir=$(ls /opt/cons3rt-agent/run | grep "Deployment")
        deploymentHome="/opt/cons3rt-agent/run/${deploymentDir}"
        export DEPLOYMENT_HOME="${deploymentHome}"
    else
        deploymentHome="${DEPLOYMENT_HOME}"
    fi
}

function read_deployment_properties() {
    local deploymentPropertiesFile="${DEPLOYMENT_HOME}/deployment-properties.sh"
    if [ ! -f ${deploymentPropertiesFile} ] ; then
        logErr "Deployment properties file not found: ${deploymentPropertiesFile}"
        return 1
    fi
    . ${deploymentPropertiesFile}
    return $?
}

function get_env() {
    logInfo "Attempting to pycons3rt environment variables..."
    . ${pycons3rtEnv}

    # Get python home
    if [ -z "${PYCONS3RT_PYTHON_HOME}" ] ; then
        logErr "Required environment vairable not found: PYCONS3RT_PYTHON_HOME"
        return 1
    else
        pythonHome="${PYCONS3RT_PYTHON_HOME}"
        logInfo "Found PYCONS3RT_PYTHON_HOME: ${pythonHome}"
    fi

    # Get python
    if [ -z "${PYCONS3RT_PYTHON}" ] ; then
        logErr "Required environment vairable not found: PYCONS3RT_PYTHON"
        return 2
    else
        pythonExe="${PYCONS3RT_PYTHON}"
        logInfo "Found PYCONS3RT_PYTHON: ${pythonExe}"
    fi

    # Get pip
    if [ -z "${PYCONS3RT_PIP}" ] ; then
        logErr "Required environment vairable not found: PYCONS3RT_PIP"
        return 3
    else
        pipExe="${PYCONS3RT_PIP}"
        logInfo "Found PYCONS3RT_PIP: ${pipExe}"
    fi

    # Get pycons3rt source dir
    if [ -z "${PYCONS3RT_SOURCE_DIR}" ] ; then
        logErr "Required environment vairable not found: PYCONS3RT_SOURCE_DIR"
        return 3
    else
        pycons3rtSourceDir="${PYCONS3RT_SOURCE_DIR}"
        logInfo "Found PYCONS3RT_SOURCE_DIR: ${pycons3rtSourceDir}"
    fi

    # Determine the source directory
    sourceDir="${pycons3rtSourceDir}/pycons3rtapi"
    logInfo "Using source directory: ${sourceDir}"

    logInfo "pycons3rt python environment variables loaded successfully"
    return 0
}

function verify_dns() {
    # Tries to resolve a domain name for 5 minutes
    # Parameters:
    # 1 - Domain Name (e.g. example.com)
    # Returns:
    # 0 - Successfully resolved domain name
    # 1 - Failed to resolve domain name
    local domainName=$1
    local count=0
    while [ ${count} -le 150 ] ; do
        logInfo "Verifying domain name resolution for ${domainName}"
        getent hosts ${domainName}
        if [ $? -ne 0 ] ; then
            logWarn "Could not resolve domain name - ${domainName} - trying again in 2 seconds..."
        else
            logInfo "Successfully resolved domain name: ${domainName}!"
            return 0
        fi
        count=$((${count}+1))
        sleep 2
    done
    logErr "Failed DNS resolution for domain name: ${domainName}"
    return 1
}

function verify_prerequisites() {
    logInfo "Verifying prerequisites are installed..."

    logInfo "Ensuring python is installed..."
    ${pythonExe} --version >> ${logFile} 2>&1
	if [ $? -ne 0 ] ; then
        logErr "Python not detected, and is a required dependency"
        return 1
    fi

    logInfo "Ensuring pip is installed..."
    ${pipExe} --version >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then
        logErr "pip is not installed, this is a required dependency"
        return 2
    fi

    logInfo "Ensuring the pycons3rt package is installed..."
    ${pythonExe} -c "import pycons3rt" >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then
        logErr "pycons3rt not detected, this is a required dependency"
        return 3
    fi
    logInfo "Verified prerequisites!"
    return 0
}

function git_clone() {
    logInfo "Attempting to git clone the pycons3rtapi repo..."

    # Verify connectivity to the git repo domain
    verify_dns ${gitServerDomainName}
    if [ $? -ne 0 ] ; then
        logErr "Unable to resolve GIT server domain name: ${gitServerDomainName}"
        return 1
    else
        logInfo "Successfully resolved domain name: ${gitServerDomainName}"
    fi

    # Determine the pycons3rtapi branch
    pycons3rtapiBranch="${defaultGitBranch}"
    if [ ! -z "${PYCONS3RTAPI_BRANCH}" ] ; then
        logInfo "Found deployment property PYCONS3RTAPI_BRANCH: ${PYCONS3RTAPI_BRANCH}"
        pycons3rtapiBranch="${PYCONS3RTAPI_BRANCH}"
    else
        logInfo "PYCONS3RTAPI_BRANCH deployment property not found, git will clone the ${pycons3rtapiBranch} branch"
    fi

    logInfo "Ensuring HOME is set..."
    if [ -z "${HOME}" ] ; then
        export HOME="/root"
    fi

    # Git clone the specified branch
    logInfo "Cloning the pycons3rtapi GIT repo..."
    for i in {1..10} ; do

        # Remove the source directory if it exists
        if [ -d ${sourceDir} ] ; then
            logInfo "Removing: ${sourceDir}"
            rm -Rf ${sourceDir} >> ${logFile} 2>&1
        fi

        logInfo "Attempting to clone the GIT repo, attempt ${i} of 10..."
        git clone -b ${pycons3rtapiBranch} --depth 1 ${pycons3rtapiGitUrl} ${sourceDir} >> ${logFile} 2>&1
        result=$?
        logInfo "git clone exited with code: ${result}"
        if [ ${result} -ne 0 ] && [ $i -ge 10 ] ; then
            logErr "Unable to clone git repo after ${i} attempts: ${gitUrl}"
            return 2
        elif [ ${result} -ne 0 ] ; then
            logWarn "Unable to clone git repo, re-trying in 5 seconds: ${gitUrl}"
            sleep 5
        else
            logInfo "Successfully cloned git repo: ${gitUrl}"
            break
        fi
    done

    # Ensure the pycons3rtapi install script can be found
    pycons3rtapiInstaller="${sourceDir}/scripts/install.sh"
    if [ ! -f ${pycons3rtapiInstaller} ] ; then
        logErr "pycons3rtapi install script not found: ${pycons3rtapiInstaller}, source code may not have been checked out or staged correctly"
        return 3
    fi
    logInfo "Found file: ${pycons3rtapiInstaller}, git clone succeeded!"
    return 0
}

function install_pip_requirements() {
    logInfo "Installing pip requirements from the requirements.txt file..."

    if [ ! -d ${sourceDir} ] ; then
        logErr "Source code directory not found, cannot install pip requirements: ${sourceDir}"
        return 1
    fi

    logInfo "Changing to directory: ${sourceDir}"
    cd ${sourceDir} >> ${logFile} 2>&1

    # Ensure the requirements file exists
    requirementsFileRelPath="./cfg/requirements.txt"
    if [ ! -f ${requirementsFileRelPath} ] ; then
        logErr "Requirements file not found at relative path: ${requirementsFileRelPath}"
        return 2
    fi

    logInfo "Using pip: ${pipExe}"
    logInfo "Attempting to install pip requirements from file at relative path: ${requirementsFileRelPath}"
    ${pipExe} install -r ${requirementsFileRelPath} >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then
        logErr "There was a problem installing pip requirements"
        return 3
    fi
    logInfo "Successfully installed pip requirements"
    return 0
}

function install_pycons3rtapi() {
    # Install the pycons3rtapi python project into the system python lib
    logInfo "Attempting to install pycons3rtapi..."
    ${pycons3rtapiInstaller} >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logInfo "pycons3rt install exited with code: ${?}"; return 1; fi
    logInfo "pycons3rtapi install completed successfully!"
    return 0
}

function run_setup_install() {
    logInfo "Attempting to run setup.py..."

    if [ ! -d ${sourceDir} ] ; then
        logErr "Source code directory not found, cannot run setup.py: ${sourceDir}"
        return 1
    fi

    logInfo "Changing to directory: ${sourceDir}"
    cd ${sourceDir} >> ${logFile} 2>&1

    # Ensure setup.py exists
    if [ ! -f setup.py ] ; then
        logErr "setup.py file not found"
        return 2
    fi

    logInfo "Running setup.py..."
    ${pythonExe} setup.py install >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem running setup.py..."; return 3; fi

    logInfo "setup.py ran successfully!"
    return 0
}

function main() {
    logInfo "Beginning ${logTag} install..."
    set_deployment_home
    read_deployment_properties
    get_env
    if [ $? -ne 0 ]; then logErr "A required environment variable is not set"; return 1; fi
    verify_prerequisites
    if [ $? -ne 0 ]; then logErr "A required prerequisite is not installed"; return 2; fi
    git_clone
    if [ $? -ne 0 ] ; then logErr "There was a problem cloning the pycons3rtapi git repo"; return 3; fi
    install_pip_requirements
    if [ $? -ne 0 ] ; then logErr "There was a problem installing one or more pip packages"; return 4; fi
    run_setup_install
    if [ $? -ne 0 ] ; then logErr "There was a problem installing pycons3rtapi"; return 5; fi
    logInfo "Completed: ${logTag} install script"
    return 0
}

# Set up the log file
mkdir -p ${logDir}
chmod 700 ${logDir}
touch ${logFile}
chmod 644 ${logFile}

main
result=$?
cat ${logFile}

logInfo "Exiting with code ${result} ..."
exit ${result}
