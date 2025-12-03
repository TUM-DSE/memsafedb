#!/usr/bin/env bash

host=$(hostname)
if [[ $host = "ace" ]]; then
  if [[ -z $1 ]]; then
    echo "Specify which flavor of CHERI you want (hybrid/pure)"
    exit 1
  fi
  nix develop .#ace-$1
else
  nix develop .#$(hostname)
fi
