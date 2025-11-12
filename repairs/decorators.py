from django.contrib.auth.decorators import login_required, user_passes_test

def store_only(view_func):
    """
    Custom decorator to restrict view access to store staff only.
    Must be used in combination with @login_required
    """
    return user_passes_test(lambda u: hasattr(u, 'staffprofile') and u.staffprofile.role == 'store')(view_func)