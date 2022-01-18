#!/bin/sh

PID=$(cat .bao_server.pid)

echo "Killing server with PID $PID"
kill -INT $PID

