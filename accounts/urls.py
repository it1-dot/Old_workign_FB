from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .views import (
    SetPasswordAPI,
    UserViewSet,
    LoginAPI,
    TeamViewSet,
    TaskViewSet,
    TodoViewSet,
    TaskAttachmentViewSet,
    SendMessageView,
    ChatHistoryView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(r"teams", TeamViewSet, basename="teams")
router.register(r"tasks", TaskViewSet, basename="tasks")
router.register(r"task-attachments", TaskAttachmentViewSet, basename="task-attachments")
router.register(r"todos", TodoViewSet, basename="todos")


urlpatterns = [
    path("", include(router.urls)),
    path("login/", LoginAPI.as_view(), name="login"), #for login to get token
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("set-password/", SetPasswordAPI.as_view(), name="set_password"), # for set-passwords after first login
    path("send/<int:receiver_id>/", SendMessageView.as_view()), # for sending a message
    path("history/<int:user_id>/", ChatHistoryView.as_view()), # for getting the chat hostory
    path('conversations/', views.ConversationListCreateAPIView.as_view(), name='conversation-list-create'),
    path('messages/', views.MessageListCreateAPIView.as_view(), name='message-list-create'),
    path('conversations/<int:conversation_id>/messages/', views.MessageByConversationAPIView.as_view(), name='conversation-messages'),
    
]
