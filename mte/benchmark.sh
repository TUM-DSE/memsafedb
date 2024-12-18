#!/usr/bin/env bash

# Runs the performance tests for a specific data structure remote device.

set -o errexit  # when a command fails, exist
set -o nounset  # fail when accessing an unset variable
set -o pipefail # fail pipeline if any command errors

DATASTRUCTURE=$1

if [ -z "$USER" ]; then
  if [ -z "$2" ]; then
    echo "USER is not set, and no parameter provided."
    exit 1
  else
    USER=$1
  fi
fi


if [ -z "$HOST" ]; then
  if [ -z "$3" ]; then
    echo "HOST is not set, and no parameter provided."
    exit 1
  else
    HOST=$3
  fi
fi

if [ -z "$PORT" ]; then
  if [ -z "$4" ]; then
    echo "PORT is not set, and no parameter provided."
    exit 1
  else
    PORT=$4
  fi
fi


# TODO: assert dependencies (connection, DS exists, cmake file has option etc)

python ./scripts/main.py --user $USER --host $HOST --port $PORT copy
python ./scripts/main.py --user $USER --host $HOST --port $PORT build --datastructure "$DATASTRUCTURE"
python ./scripts/main.py --user $USER --host $HOST --port $PORT analyse --datastructure "$DATASTRUCTURE"
