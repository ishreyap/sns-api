from pydantic import BaseModel
from typing import Optional

class FAQCreateRequest(BaseModel):
    question: str
    

class FAQSearchRequest(BaseModel):
    query: str
