# backend/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from .api import stock

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
app.include_router(stock.router)
