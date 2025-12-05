from fastapi import APIRouter
from app.api import tickets, tags

api_router = APIRouter()
api_router.include_router(tickets.router)
api_router.include_router(tags.router)
