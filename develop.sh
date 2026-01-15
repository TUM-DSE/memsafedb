#!/usr/bin/env bash

host=$(hostname)
if [[ $host = "ace" ]]; then
  if [[ -z $1 ]]; then
    echo "Specify which flavor of CHERI you want (aarch64/cheri)"
    exit 1
  fi
  nix develop .#ace-$1
else
  nix develop .#$(hostname)
fi
