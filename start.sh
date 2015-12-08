#!/bin/bash

echo "killing server:"
screen -ls | grep roadwars | cut -d. -f1 | awk '{print $1}' | xargs kill
echo "done"

echo "starting RoadWars server:"
screen -dmS roadwars python3 server.py
echo "OK"
