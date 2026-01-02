from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import User, Team


# --------------------------------------------------
# CUSTOM USER CREATION FORM (NO PASSWORD)
# --------------------------------------------------
class UserCreateForm(forms.ModelForm):
    """
    Allow admin to create user without password.
    Password will be set later by user.
    """
    class Meta:
        model = User
        fields = (
            "user_id",
            "email",
            "is_admin",
            "is_teamlead",
            "is_active",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()  # IMPORTANT
        if commit:
            user.save()
        return user


# --------------------------------------------------
# USER ADMIN
# --------------------------------------------------
class UserAdmin(BaseUserAdmin):
    add_form = UserCreateForm
    model = User

    list_display = (
        "user_id",
        "email",
        "is_admin",
        "is_teamlead",
        "is_active",
    )

    list_filter = ("is_admin", "is_teamlead", "is_active")
    search_fields = ("user_id", "email")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("user_id", "email")}),
        (
            "Permissions",
            {"fields": ("is_admin", "is_teamlead", "is_active")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "user_id",
                    "email",
                    "is_admin",
                    "is_teamlead",
                    "is_active",
                ),
            },
        ),
    )


admin.site.register(User, UserAdmin)


# --------------------------------------------------
# TEAM ADMIN
# --------------------------------------------------
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name", "created_by__user_id")
    list_filter = ("created_at",)

    # Enables multi-select UI for members
    filter_horizontal = ("members",)
    exclude = ("created_by",)

    def save_model(self, request, obj, form, change):
        """
        Automatically set creator as logged-in user
        """
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

