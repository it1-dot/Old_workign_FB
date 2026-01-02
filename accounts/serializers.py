from rest_framework import serializers,generics, permissions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Team, Task, TaskAttachment, Todo, Message, Conversation

# =====================================================
# USER SERIALIZERS
# =====================================================

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "user_id", "email", "is_admin", "is_teamlead", "is_active"]


class CreateUserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(required=False, default=False)
    is_teamlead = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = ["user_id", "email", "is_admin", "is_teamlead", "is_active"]

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_unusable_password()
        user.save()
        return user


class SetPasswordSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user = User.objects.get(
                user_id=data["user_id"],
                email=data["email"]
            )
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        if user.has_usable_password():
            raise serializers.ValidationError("Password already set")

        data["user"] = user
        return data

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.is_active = True
        user.save()
        return user


class LoginSerializer(TokenObtainPairSerializer):
    username_field = "user_id"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["user_id"] = user.user_id
        token["email"] = user.email
        token["role"] = (
            "ADMIN" if user.is_admin else
            "TEAM_LEAD" if user.is_teamlead else
            "USER"
        )
        return token


# =====================================================
# TEAM SERIALIZERS
# =====================================================

class TeamSerializer(serializers.ModelSerializer):
    members = serializers.SlugRelatedField(
        many=True,
        slug_field="user_id",
        queryset=User.objects.all(),
        required=False
    )
    created_by = serializers.SlugRelatedField(
        slug_field="user_id",
        read_only=True
    )

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "description",
            "created_by",
            "members",
            "created_at",
        ]


class CreateTeamSerializer(serializers.ModelSerializer):
    members = serializers.SlugRelatedField(
        many=True,
        slug_field="user_id",
        queryset=User.objects.all(),
        required=False
    )

    class Meta:
        model = Team
        fields = ["name", "description", "members"]


# =====================================================
# TASK SERIALIZERS
# =====================================================

class SubTaskSerializer(serializers.ModelSerializer):
    # assigned_to = serializers.SlugRelatedField(
    #     slug_field="user_id",
    #     read_only=True
    # )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            # "assigned_to",
            "estimated_start_date",
            "estimated_end_date",
            "priority",
            "status",
        ]


class SubtaskCreateSerializer(serializers.Serializer):
    # id = serializers.IntegerField(required=False)
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    # assigned_to = serializers.SlugRelatedField(
    #     slug_field="user_id",
    #     queryset=User.objects.all()
    # )
    estimated_start_date = serializers.DateField()
    estimated_end_date = serializers.DateField()
    priority = serializers.ChoiceField(choices=Task.PRIORITY_CHOICES)
    status = serializers.ChoiceField(
        choices=Task.STATUS_CHOICES,
        required=False,
        default="PENDING"
    )


class TaskSerializer(serializers.ModelSerializer):
    subtasks_data = SubtaskCreateSerializer(many=True, write_only=True, required=False)
    subtasks = SubTaskSerializer(many=True, read_only=True)
    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "estimated_start_date",
            "estimated_end_date",
            "priority",
            "status",
            "subtasks",
            "subtasks_data",
        ]

    def create(self, validated_data):
        subtasks_data = validated_data.pop("subtasks_data", [])
        user = self.context["request"].user
        validated_data["created_by"] = user

        main_task = Task.objects.create(**validated_data)

        # create subtasks
        for sub in subtasks_data:
            Task.objects.create(
                parent_task=main_task,
                created_by=user,
                **sub
            )

        return main_task

    def update(self, instance, validated_data):
        subtasks_data = validated_data.pop("subtasks_data", [])

        # update main task
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        user = self.context["request"].user

        # update / create subtasks
        for sub in subtasks_data:
            sub_id = sub.get("id")
            if sub_id:
                subtask = Task.objects.filter(id=sub_id, parent_task=instance).first()
                if subtask:
                    for key, value in sub.items():
                        if key != "id":
                            setattr(subtask, key, value)
                    subtask.save()
            else:
                Task.objects.create(
                    parent_task=instance,
                    created_by=user,
                    **sub
                )
        return instance
    


    def get_queryset(self):
        return Task.objects.filter(
            created_by=self.request.user,
            parent_task__isnull=True
        ).prefetch_related("subtasks")
    

# =====================================================
# ATTACHMENTS & TO DO
# =====================================================

class TaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ["id", "task", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class TodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Todo
        fields = ["id", "title", "date", "is_done", "created_by"]
        read_only_fields = ["id", "created_by"]


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True) 
    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "text", "is_read", "timestamp"]



class ConversationSerializer(serializers.ModelSerializer):
    user1 = serializers.CharField(source="user1.user_id", read_only=True)
    user2 = serializers.CharField(source="user2.user_id", read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "user1", "user2", "created_at"]


class MessageListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(
            conversation__user1=self.request.user
        ) | Message.objects.filter(
            conversation__user2=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
