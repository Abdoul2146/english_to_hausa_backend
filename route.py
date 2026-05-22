from fastapi import APIRouter
from api.endpoints import video_to_audio, translate, tts

api_router = APIRouter(prefix="/api")

api_router.include_router(video_to_audio.router)
api_router.include_router(translate.router)
api_router.include_router(tts.router)
