from fastapi import APIRouter

from .routes import (
    attachments,
    auth,
    indexing,
    library,
    scripture,
    search,
    sermons,
    service_access,
    users,
    verses,
    widget,
)

api_router = APIRouter()

api_router.include_router(attachments.router, prefix="/api/attachments")
api_router.include_router(auth.router, prefix="/api/auth")
api_router.include_router(service_access.router, prefix="/api/service-accounts")
api_router.include_router(library.router, prefix="/api/library")
api_router.include_router(search.router, prefix="/api/search")
api_router.include_router(indexing.router, prefix="/api/index")
api_router.include_router(sermons.router, prefix="/api/sermons")
api_router.include_router(scripture.router, prefix="/api/scripture")
api_router.include_router(users.router, prefix="/api/users")
api_router.include_router(verses.router, prefix="/api/verses")
api_router.include_router(widget.router, prefix="/api/widget")
