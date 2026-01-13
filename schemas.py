from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = '1'

class ChatResponse(BaseModel):
    reply: Optional[str] = None
    pdf_path: Optional[str]= None
    status : str