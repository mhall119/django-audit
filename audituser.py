try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

def get_current_user():
    "Return the owner of the current thread"
    return getattr(_thread_locals, 'user', None)

def get_current_user_id():
    user = get_current_user()
    if (user != None):
        return getattr(user, 'id', 0)
    else:
        return 0
    
def set_current_user(user):
    "Set the owner of the current thread"
    _thread_locals.user = user
    

