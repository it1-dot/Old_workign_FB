from rest_framework.permissions import BasePermission
from .models import Team


class IsAdmin(BasePermission):
    """
    Allows access only to Admin users
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_admin
        )


class IsTeamLead(BasePermission):
    """
    Allows access only to Team Leads
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_teamlead
        )


class IsAdminOrTeamLead(BasePermission):
    """
    Allows access to Admin OR Team Lead
    (USED FOR TEAM CREATION)
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_admin or request.user.is_teamlead)
        )


class IsTeamCreator(BasePermission):
    """
    Only TEAM LEAD who created the team can edit it.
    ADMIN is NOT allowed to edit.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        return user.is_teamlead and obj.created_by == user



class IsTeamCreatorForTask(BasePermission):
    """
    Allow task creation only if user is the creator of the team
    """

    def has_permission(self, request, view):
        # Allow all other actions
        if view.action != "create":
            return True

        team_id = request.data.get("team")
        if not team_id:
            return False

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return False

        return team.created_by == request.user