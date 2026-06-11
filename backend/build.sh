#!/usr/bin/env bash
set -e
pip install --upgrade pip

# Install httpx and httpcore first with pinned versions
pip install httpx==0.27.2 httpcore==1.0.5

# Install everything else
pip install flask==3.0.3 flask-cors==4.0.1 flask-jwt-extended==4.6.0 flask-sqlalchemy==3.1.1
pip install groq==0.9.0
pip install qdrant-client==1.10.1
pip install langchain==0.2.11 langchain-community==0.2.10
pip install sentence-transformers==3.0.1
pip install reportlab==4.2.2 pypdf==4.3.1
pip install python-dotenv==1.0.1 requests==2.32.3
pip install beautifulsoup4==4.12.3 bcrypt==4.1.3
pip install razorpay==1.4.1 ddgs==9.2.0
pip install gunicorn==22.0.0 psycopg2-binary==2.9.9