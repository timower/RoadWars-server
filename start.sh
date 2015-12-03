#!/bin/bash

echo "starting RoadWars server:"
screen -dmS roadwars python3 server.py
echo "OK"
echo "starting web server:"
screen -dmS web python3 web_server.py
echo "OK"
