#!/bin/bash
# $1 is project e.g. TAIJI
# $2 onwards is command contained in double quotes
export SUBJECTS_DIR=$1
shift
"$@"
