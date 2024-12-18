#!/usr/bin/env bash

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

if [ -z "$USER" ]; then
  if [ -z "$1" ]; then
    echo "USER is not set, and no parameter provided."
    exit 1
  else
    USER=$1
  fi
fi


if [ -z "$HOST" ]; then
  if [ -z "$2" ]; then
    echo "HOST is not set, and no parameter provided."
    exit 1
  else
    HOST=$2
  fi
fi

if [ -z "$PORT" ]; then
  if [ -z "$3" ]; then
    echo "PORT is not set, and no parameter provided."
    exit 1
  else
    PORT=$3
  fi
fi

python ./scripts/main.py --user $USER --host $HOST --port $PORT copy
python ./scripts/main.py --user $USER --host $HOST --port $PORT build --datastructure  chashtabledb
python ./scripts/main.py --user $USER --host $HOST --port $PORT analyse --datastructure chashtabledb
