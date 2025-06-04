#!/usr/bin/env bash
###############################################################################
# run.sh
# ======
#
# Description:           Launch script
# Author:                Michael De Pasquale
# Creation Date:         2025-05-28
# Modification Date:     2025-06-04
#
###############################################################################

# NOTE: You may need to adjust the sensitivity values for your setup.

_usage() {
    echo "Usage: $0 GAME"
    echo ""
    echo "Supported games are 'tf2' and 'cs2'"
}

_findWindow() {
    echo "$(xwininfo -name "$1" | grep -oP "(?<=Window id: )0x\w+")"
}

if [ $# != "1" ]; then
    echo "Error: Expected 1 argument"
    _usage

    exit 1
fi


if [ "$1" == "cs2" ]; then
    uv run python main.py \
        --confidence 0.35 \
        --sensitivity 1.25 \
        --triggerbox-scale 0.75 \
        --interp-scale 4 \
        $(_findWindow "Counter-Strike 2")
elif [ "$1" == "tf2" ]; then
    uv run python main.py \
        --sensitivity 0.43 \
        --confidence 0.32 \
        --triggerbox-scale 0.7 \
        $(_findWindow "Team Fortress 2 - Vulkan - 64 Bit")
else
    echo "Unrecognised game '$1'"
    _usage
fi
