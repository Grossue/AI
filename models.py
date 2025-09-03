from pydantic import BaseModel
from datetime import datetime
from typing import List

class ArticleMemoryItem(BaseModel):
    title: str
    date_time: datetime

class UserHistoryRequest(BaseModel):
    history: List[ArticleMemoryItem]