from django.contrib import admin

# Register your models here.
from django.contrib.sessions.models import Session

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """
    Custom admin view for the Session model to display decoded session data.
    """
    list_display = ['session_key', '_session_data', 'expire_date']

    def _session_data(self, obj):
        """
        Decodes the session data to make it human-readable in the admin.
        """
        return obj.get_decoded()

    def has_add_permission(self, request):
        # Sessions are created automatically, so disable manual creation.
        return False

    def has_change_permission(self, request, obj=None):
        # It's generally not safe to edit sessions directly.
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow deletion of sessions to manually log out users.
        return True