from fastapi import APIRouter
from app.api.routers import orders, chat, knowledge, auth, stats, evaluation, tickets

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(orders.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)
api_router.include_router(stats.router)
api_router.include_router(evaluation.router)
api_router.include_router(tickets.router)
