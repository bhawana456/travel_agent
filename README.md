NOMAD – AI Powered Travel Agent

NOMAD is an AI-powered travel planning assistant built using LangGraph, FastAPI, and LLMs.
It interacts with users in a conversational manner, collects travel details step by step, generates a comprehensive travel guide, and exports it as a PDF.

Features:
Conversational travel planning

Multi-agent architecture using LangGraph

Intelligent information extraction (destination, dates, currency, language, etc.)

Tool-assisted data fetching (flights, hotels, currency)

Automatic PDF travel guide generation

FastAPI-based backend

Stateful conversations using thread_id

Agents Used

Nomad Agent – Handles user conversation and follow-ups

Proxy Agent – Extracts structured travel information

Travel Guide Agent – Generates a structured travel guide

PDF Generator Node – Converts the guide into a styled PDF

Project Structure:
travel_agent/
│
├── app.py                  # FastAPI entry point
├── graph.py                # LangGraph workflow & agents
├── schemas.py              # Request/Response models
├── tools.py                # External tools (currency, flight, hotel)
├── prompt.py               # System & agent prompts
├── utility.py              # Prompt builders & helpers               
├── outputs/                # Generated PDFs
├── .env                    # API keys
├── .gitignore
└── README.md

Installation & Setup

1. Clone the repository
    
    git clone  https://github.com/bhawana456/travel_agent.git
    
    cd travel_agent

2. Create & activate virtual environment (uv)
    
    uv venv
    
    source .venv/bin/activate 

3. Install required dependencies 
    
    uv add 

4. Run the application
    
    uvicorn app:app --host 0.0.0.0 --port 5000 --reload


Conversation State

Maintained using LangGraph memory

Controlled via thread_id

Allows multi-turn conversations without losing context

Future Enhancements

Frontend(Gradio)

License

This project is for educational and experimental purposes.