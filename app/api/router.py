from fastapi import APIRouter

from .routes import attachments, auth, library, scripture, sermons, verses, widget

api_router = APIRouter()

api_router.include_router(attachments.router, prefix="/api/attachments")
api_router.include_router(auth.router, prefix="/api/auth")
api_router.include_router(library.router, prefix="/api/library")
api_router.include_router(sermons.router, prefix="/api/sermons")
api_router.include_router(scripture.router, prefix="/api/scripture")
api_router.include_router(verses.router, prefix="/api/verses")
api_router.include_router(widget.router, prefix="/api/widget")
