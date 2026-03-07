from fastapi import APIRouter

from .routes import attachments, auth, search, sermons, verses, widget

api_router = APIRouter()

api_router.include_router(attachments.router, prefix="/api/attachments")
api_router.include_router(auth.router, prefix="/api/auth")
api_router.include_router(search.router, prefix="/api/search")
api_router.include_router(sermons.router, prefix="/api/sermons")
api_router.include_router(verses.router, prefix="/api/verses")
api_router.include_router(widget.router, prefix="/api/widget")
