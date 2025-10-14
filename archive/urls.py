from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.sermon_list, name='sermon_list'),
    path('sermons/new', views.sermon_create, name='sermon_create'),
    path('sermons/<int:pk>', views.sermon_detail, name='sermon_detail'),
    path('sermons/<int:pk>/edit', views.sermon_edit, name='sermon_edit'),
    path('sermons/<int:pk>/ui/passage/preview', views.passage_preview, name='passage_preview'),
    path('sermons/<int:pk>/ui/passage/add', views.passage_add, name='passage_add'),
    path('sermons/<int:pk>/ui/passage/<int:ord>/edit', views.passage_edit, name='passage_edit'),
    path('sermons/<int:pk>/ui/passage/<int:ord>/delete', views.passage_delete, name='passage_delete'),
    path('sermons/<int:pk>/attachments', views.attachment_upload, name='attachment_upload'),
    path('sermons/<int:pk>/attachments/<int:att_id>/delete', views.attachment_delete, name='attachment_delete'),
    path('verses/add', views.verse_editor, name='verse_editor'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

