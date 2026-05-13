from .models import SystemActivityLog

def log_activity(user, action, details=None):
    """
    Log a system activity to the database.
    user: The user object performing the action
    action: String describing the action (e.g., 'USER_CREATED')
    details: Dictionary with additional context
    """
    try:
        SystemActivityLog.objects.create(
            user_id=user.id if hasattr(user, 'id') else None,
            action=action,
            details=details or {}
        )
    except Exception as e:
        # Prevent logging failure from breaking the main transaction
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log activity: {str(e)}")
