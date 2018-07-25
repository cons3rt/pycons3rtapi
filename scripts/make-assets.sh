#!/bin/bash

# The purpose of this script is make the pycons3rtapi assets for import into CONS3RT

# Set log commands
logTag="make-assets"

######################### GLOBAL VARIABLES #########################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="${SCRIPT_DIR}/.."
ASSET_DIR="${SCRIPT_DIR}/../asset"
BUILD_DIR="${ASSET_DIR}/../build"
resultSet=()

####################### END GLOBAL VARIABLES #######################

# Logging functions
function timestamp() { date "+%F %T"; }
function logInfo() { echo -e "$(timestamp) ${logTag} [INFO]: ${1}"; }
function logWarn() { echo -e "$(timestamp) ${logTag} [WARN]: ${1}"; }
function logErr() { echo -e "$(timestamp) ${logTag} [ERROR]: ${1}"; }

function create_asset_zip() {
    cd $1
    zipFileName=$(echo $(pwd) | awk -F '/' '{print $NF}')
    zipFilePath="${BUILD_DIR}/${zipFileName}.zip"
    find . -name ".DS_Store" -exec rm {} \;
    find . -type f -name "._*" -exec rm {} \;
    zip -r ${zipFilePath} asset.properties doc media scripts config data src README* LICENSE* HELP* -x "doc\._*" -x "media\._*" -x "scripts\._*" -x "._*" -x \"*.DS_Store*\" -x \".DS_Store\"  -x \"*.svn\" -x \"*.git\" -x media\MEDIA_README > /dev/null 2>&1
    result=$?
    logInfo "Created asset: build/${zipFileName}.zip"
    return ${result}
}

function make_asset() {
    assetName="asset-pycons3rtapi-$1"
    assetCreationDir="${BUILD_DIR}/${assetName}"
    subAssetDir="${ASSET_DIR}/$1"

    # Copy the asset.properties and scripts directories
    mkdir -p ${assetCreationDir}/scripts
    cp -f ${subAssetDir}/asset.properties ${assetCreationDir}/
    cp -f ${subAssetDir}/scripts/* ${assetCreationDir}/scripts/

    # Copy the README file to the asset
    if [ -f ${subAssetDir}/README.md ] ; then
        cp -f ${subAssetDir}/README.md ${assetCreationDir}/
    else
        cp -f ${REPO_DIR}/README.md ${assetCreationDir}/
    fi

    # Copy license file to asset
    cp -f ${REPO_DIR}/LICENSE ${assetCreationDir}/

    # Copy the media directory if it exists
    if [ -d ${subAssetDir}/media ] ; then
        mkdir -p ${assetCreationDir}/media
        cp -f ${subAssetDir}/media/* ${assetCreationDir}/media/
    fi

    if [ -z $2 ] ; then
        :
    else
        if [ ! -f $2 ] ; then
            logErr "Additional file not found for asset $1, stage locally before running: $2"
            return 1
        else
            logInfo "Additional file found for asset $1, adding to media directory: $2"
            mkdir -p ${assetCreationDir}/media
            cp -f $2 ${assetCreationDir}/media/
        fi
    fi

    for resultCheck in "${resultSet[@]}" ; do
        if [ ${resultCheck} -ne 0 ] ; then
            logErr "Non-zero exit code found: ${resultCheck}"
            return 2
        fi
    done

    # Create the asset zip file
    create_asset_zip ${assetCreationDir}
    if [ $? -ne 0 ] ; then
        logErr "Unable to create asset zip file"
        return 3
    fi

    # Clean up
    rm -Rf ${assetCreationDir}
}

mkdir -p ${BUILD_DIR}

make_asset "linux"
if [ $? -ne 0 ] ; then
    logErr "Unable to create the linux asset"
    exit 1
fi

make_asset "windows"
if [ $? -ne 0 ] ; then
    logErr "Unable to create the Windows asset"
    exit 2
fi

exit 0
