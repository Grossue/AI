from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

import router
from dotenv import load_dotenv

app = FastAPI()

origins = [
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

app.include_router(router.router)
