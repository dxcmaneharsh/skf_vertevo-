#!/bin/bash
# Start the Streamlit application on the port provided by Cloud Foundry
streamlit run skf_app.py --server.port $PORT --server.address 0.0.0.0
