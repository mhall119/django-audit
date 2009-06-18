import audituser

class CaptureRequestUser(object):
    "Middleware that captures the current HTTP request user for auditing purposes"
    
    def process_request(self, request):
        audituser.set_current_user(getattr(request, 'user', None))

