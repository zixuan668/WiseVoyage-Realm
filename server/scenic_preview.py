"""Run the scenic-detail preview against the configured PostgreSQL database."""
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
from server.base.routers.tour_experience import DB_ENGINE, ScenicDraftStop, router

from server.base.routers.tour_experience import ScenicJourney, ScenicArrival, ScenicReview, ScenicDraftSettings, ScenicParkServices
for model in (ScenicDraftStop, ScenicJourney, ScenicArrival, ScenicReview, ScenicDraftSettings, ScenicParkServices):
    model.__table__.create(DB_ENGINE, checkfirst=True)
app = FastAPI()
app.include_router(router)

from server.base.routers import tour_chat, avatar, xingyun, tts
from fastapi.staticfiles import StaticFiles
for module in (tour_chat, avatar, xingyun, tts):
    app.include_router(module.router)
app.mount('/api/v1/files', StaticFiles(directory='static'), name='preview-files')
