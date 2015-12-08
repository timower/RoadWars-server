#!/bin/bash

echo "killing server:"
screen -ls | grep roadwars | cut -d. -f1 | awk '{print $1}' | xargs kill
screen -ls | grep web | cut -d. -f1 | awk '{print $1}' | xargs kill
echo "done"

echo "starting RoadWars server:"
screen -dmS roadwars python3 server.py
echo "OK"
sleep 1
echo "starting web server:"
screen -dmS web python3 web_server.py
echo "OK"
