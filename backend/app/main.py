# backend/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from .api import stock
from .graph.build_graph import build_app_graph
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

class QueryRequest(BaseModel):
    query: str

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(stock.router)

# Build the LangGraph application
graph_app = build_app_graph()

@app.post("/graph")
async def handle_graph_query(request: QueryRequest):
    """Handle queries through the LangGraph routing system"""
    try:
        print(f"🔧 MAIN SERVER - Received query: '{request.query}'")
        
        # Execute the graph with the user query
        result = await graph_app.ainvoke({"input": request.query})
        
        print(f"🔧 MAIN SERVER - Graph result: {result}")
        
        return {"response": result.get("output", "No output received")}
        
    except Exception as e:
        print(f"❌ Error in graph execution: {e}")
        return {"error": str(e)}
