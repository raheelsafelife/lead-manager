#!/bin/bash

# Initialize the database
python create_db.py

# Start FastAPI in the background on port 8000
uvicorn api_server:app --host 0.0.0.0 --port 8000 &

# Start Streamlit on the port provided by Railway
streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
