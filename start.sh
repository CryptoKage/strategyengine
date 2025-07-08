#!/bin/bash

# This script starts your FastAPI server on the port Render assigns.

echo "Starting FastAPI server..."

# Run the server on 0.0.0.0 using the dynamic port provided by Render
uvicorn main_api:app --host 0.0.0.0 --port $PORT
