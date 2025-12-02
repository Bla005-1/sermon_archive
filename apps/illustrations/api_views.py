import itertools
from collections import defaultdict
from typing import Dict, List

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer, CharField, IntegerField
from rest_framework.views import APIView


class IllustrationSerializer(Serializer):
    id = IntegerField(read_only=True)
    title = CharField(max_length=255)
    body = CharField()


_ILLUSTRATIONS: Dict[int, dict] = {}
_SERMON_LINKS: Dict[int, List[int]] = defaultdict(list)
_COUNTER = itertools.count(1)


def _save_illustration(data: dict) -> dict:
    illustration_id = next(_COUNTER)
    stored = {"id": illustration_id, **data}
    _ILLUSTRATIONS[illustration_id] = stored
    return stored


def _update_illustration(pk: int, data: dict) -> dict:
    existing = _ILLUSTRATIONS.get(pk)
    if not existing:
        return None
    existing.update(data)
    return existing


class IllustrationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(list(_ILLUSTRATIONS.values()))

    def post(self, request):
        serializer = IllustrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved = _save_illustration(serializer.validated_data)
        return Response(saved, status=status.HTTP_201_CREATED)


class IllustrationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        data = _ILLUSTRATIONS.get(pk)
        if not data:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(data)

    def patch(self, request, pk: int):
        data = _ILLUSTRATIONS.get(pk)
        if not data:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = IllustrationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = _update_illustration(pk, serializer.validated_data)
        return Response(updated)

    def delete(self, request, pk: int):
        removed = _ILLUSTRATIONS.pop(pk, None)
        if removed is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        for _, ids in _SERMON_LINKS.items():
            if pk in ids:
                ids.remove(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SermonIllustrationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sermon_id: int):
        ids = _SERMON_LINKS.get(sermon_id, [])
        return Response([_ILLUSTRATIONS[i] for i in ids if i in _ILLUSTRATIONS])

    def post(self, request, sermon_id: int):
        serializer = IllustrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved = _save_illustration(serializer.validated_data)
        _SERMON_LINKS[sermon_id].append(saved["id"])
        return Response(saved, status=status.HTTP_201_CREATED)


class SermonIllustrationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sermon_id: int, illustration_id: int):
        data = _ILLUSTRATIONS.get(illustration_id)
        if not data:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(data)

    def post(self, request, sermon_id: int, illustration_id: int):
        if illustration_id not in _ILLUSTRATIONS:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if illustration_id not in _SERMON_LINKS[sermon_id]:
            _SERMON_LINKS[sermon_id].append(illustration_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, sermon_id: int, illustration_id: int):
        if illustration_id in _SERMON_LINKS.get(sermon_id, []):
            _SERMON_LINKS[sermon_id].remove(illustration_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
