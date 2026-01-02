from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.conf import settings


# =====================================================
# USER MANAGER
# =====================================================

class UserManager(BaseUserManager):

    def create_user(self, user_id, email, password=None, **extra_fields):
        if not user_id:
            raise ValueError("User ID is required")
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(
            user_id=user_id,
            email=email,
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, email, password, **extra_fields):
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(user_id, email, password, **extra_fields)


# =====================================================
# USER MODEL
# =====================================================

class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)

    is_admin = models.BooleanField(default=False)
    is_teamlead = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "user_id"
    REQUIRED_FIELDS = ["email"]

    objects = UserManager()

    def __str__(self):
        return self.user_id

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin


# =====================================================
# TEAM MODEL
# =====================================================

class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_teams"
    )

    members = models.ManyToManyField(
        User,
        related_name="teams",
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


# =====================================================
# TASK MODEL (Main Task + Subtask)
# =====================================================

class Task(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )

    # team = models.ForeignKey(
    #     Team,
    #     on_delete=models.CASCADE,
    #     related_name="tasks"
    # )

    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks'
    )

    # assigned_to = models.ForeignKey(
    #     User,
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name="assigned_subtasks"
    # )

    estimated_start_date = models.DateField()
    estimated_end_date = models.DateField()

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='MEDIUM'
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def is_subtask(self):
        return self.parent_task is not None

    def __str__(self):
        return self.title


# =====================================================
# TASK ATTACHMENT
# =====================================================

class TaskAttachment(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='task_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Attachment for {self.task.title}"


# =====================================================
# TO DO MODEL
# =====================================================

class Todo(models.Model):
    title = models.CharField(max_length=255)
    date = models.DateField()
    is_done = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return self.title


class Conversation(models.Model):
    """
    Represents a private chat between two users.
    """
    user1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversations_as_user1"
    )
    user2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversations_as_user2"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure no duplicate conversations in any order
        constraints = [
            models.UniqueConstraint(
                fields=["user1", "user2"],
                name="unique_conversation_pair"
            ),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Always store user1 as the one with smaller ID
        if self.user1.id > self.user2.id:
            self.user1, self.user2 = self.user2, self.user1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Conversation: {self.user1.user_id} ↔ {self.user2.user_id}"



class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save()


