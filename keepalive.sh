#!/bin/bash

while true; do
  for var in "$@"; do
    if ! adb devices | grep -q $var; then
     d=$(date "+%Y-%m-%d @ %H:%M:%S")
     echo $d: Connection to $var lost, reconnecting...
     adb connect $var
    fi
    sleep 1.5
  done
done