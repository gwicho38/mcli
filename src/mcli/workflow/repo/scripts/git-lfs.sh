#!/bin/sh -e

REMOTE=${REMOTE:-origin}

# push git lfs objects only
GIT_DIR=$(git rev-parse --git-dir)
# shellcheck disable=SC2046 # one argument per object id
git lfs push ${REMOTE} --object-id $(find ${GIT_DIR}/lfs/objects/ -type f -printf "%f ")
