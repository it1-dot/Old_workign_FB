"""
views.py

Contains API views for:
- User management
- Authentication (JWT)
- Team management
- Task management
"""

from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from .models import Conversation, Message
from .serializers import MessageSerializer
from django.contrib.auth import get_user_model
from .models import Task, TaskAttachment, User, Team, Todo
from .permissions import (
    IsAdmin,
    IsAdminOrTeamLead,
)
from .serializers import (
    UserSerializer,
    TeamSerializer,
    TaskSerializer,
    LoginSerializer,
    CreateTeamSerializer,
    CreateUserSerializer,
    SetPasswordSerializer,
    TaskAttachmentSerializer,
    TodoSerializer,
    SubtaskCreateSerializer,
    ConversationSerializer, 
    MessageSerializer
    
)

# ======================================================
# SET PASSWORD
# ======================================================

class SetPasswordAPI(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = SetPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password set successfully"},
            status=status.HTTP_200_OK
        )


# ======================================================
# USER MANAGEMENT
# ======================================================

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "list":
            return [IsAuthenticated(), IsAdminOrTeamLead()]

        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
                                                                                    
        return [IsAuthenticated()]

    def create(self, request):
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )


# ======================================================
# LOGIN
# ======================================================

class LoginAPI(TokenObtainPairView):
    serializer_class = LoginSerializer


# ======================================================
# TEAM MANAGEMENT
# ======================================================

class IsTeamCreator(BasePermission):
    """
    Only the team creator can edit the team.
    """
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsTeamCreator()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateTeamSerializer
        return TeamSerializer

    def perform_create(self, serializer):
        team = serializer.save(created_by=self.request.user)
        team.members.add(self.request.user)
        members = serializer.validated_data.get("members", [])
        if members:
            team.members.add(*members)

    def perform_update(self, serializer):
        team = serializer.save()
        members = serializer.validated_data.get("members", None)
        if members is not None:
            team.members.set(members)

    def get_queryset(self):
        user = self.request.user
        if self.action in ["update", "partial_update", "destroy"]:
            return Team.objects.filter(created_by=user)
        return Team.objects.filter(
            models.Q(created_by=user) | models.Q(members=user)
        ).distinct()


# ======================================================
# TASK MANAGEMENT
# ======================================================

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(
            created_by=self.request.user,
            parent_task__isnull=True
        ).prefetch_related("subtasks")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def add_subtask(self, request, pk=None):
    # Explicitly fetch parent task WITHOUT queryset restriction
        parent_task = get_object_or_404(
            Task,
            id=pk,
            created_by=request.user,
            parent_task__isnull=True
        )
        serializer = SubtaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        Task.objects.create(
            parent_task=parent_task,
            created_by=request.user,
            **serializer.validated_data
        )

        return Response(
            {"detail": "Subtask created successfully"},
            status=status.HTTP_201_CREATED
            )

    
    
    def get_object(self):
        """
        Allow fetching ANY task (main task)
        for add_subtask action
        """
        return get_object_or_404(
            Task,
            id=self.kwargs["pk"],
            created_by=self.request.user
        )


# ======================================================
# TASK ATTACHMENTS
# ======================================================

class TaskAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskAttachment.objects.filter(
            task__team__members=self.request.user
        )


# ======================================================
# TO DO
# ======================================================

class TodoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        date_str = request.query_params.get("date")
        if date_str:
            todos = Todo.objects.filter(
                date=date_str,
                created_by=request.user,
                is_done=False
            )
        else:
            todos = Todo.objects.filter(
                created_by=request.user,
                is_done=False
            )

        serializer = TodoSerializer(todos, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = TodoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            todo = Todo.objects.get(pk=pk, created_by=request.user)
        except Todo.DoesNotExist:
            return Response(
                {"error": "Todo not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        todo.is_done = True
        todo.save()
        return Response({"status": "completed"})

# from django.core.mail import send_mail

# class ForgotPasswordOTPAPI(generics.GenericAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = ForgotPasswordOTPSerializer

#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = User.objects.get(email=serializer.validated_data["email"])

#         otp_obj = PasswordResetOTP.objects.create(user=user)

#         # Send OTP via email
#         send_mail(
#         subject="Your Password Reset OTP",
#         message=f"Your OTP is: {otp_obj.otp}\nValid for 15 minutes.",
#         from_email=None,  # uses DEFAULT_FROM_EMAIL
#         recipient_list=[user.email],
#         fail_silently=False,
# )


#         return Response({"message": "OTP sent to your email"}, status=status.HTTP_200_OK)


# class ResetPasswordOTPAPI(generics.GenericAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = ResetPasswordOTPSerializer

#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response({"detail": "Password reset successful"}, status=status.HTTP_200_OK)



User = get_user_model()


class SendMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, receiver_id):
        receiver = User.objects.get(id=receiver_id)
        conversation, _ = get_or_create_conversation(request.user, receiver)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            text=request.data["text"]
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)



class ChatHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        other_user = User.objects.get(id=user_id)
        conversation, _ = get_or_create_conversation(request.user, other_user)
        messages = conversation.messages.order_by("timestamp")
        return Response(MessageSerializer(messages, many=True).data)



def get_or_create_conversation(user1, user2):
    u1, u2 = sorted([user1, user2], key=lambda u: u.id)
    return Conversation.objects.get_or_create(user1=u1, user2=u2)


# List/Create Messages
class MessageListCreateAPIView(generics.ListCreateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

# Messages by Conversation
class MessageByConversationAPIView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs["conversation_id"]
        conversation = Conversation.objects.get(id=conversation_id)
        if self.request.user not in [conversation.user1, conversation.user2]:
            return Message.objects.none()
        return conversation.messages.order_by("timestamp")

    def perform_create(self, serializer):
        conversation_id = self.kwargs["conversation_id"]
        conversation = Conversation.objects.get(id=conversation_id)
        serializer.save(sender=self.request.user, conversation=conversation)


# List / Create Conversations
class ConversationListCreateAPIView(generics.ListCreateAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return conversations that include the logged-in user
        user = self.request.user
        return Conversation.objects.filter(user1=user) | Conversation.objects.filter(user2=user)

    def perform_create(self, serializer):
        serializer.save(user1=self.request.user)



