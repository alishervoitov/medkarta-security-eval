from django.conf import settings


class SecurityHeadersMiddleware:
    """Stands in for the nginx headers of the production system (D7)."""

    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if "F7" not in settings.FAULTS:  # FAULT F7: headers removed
            for k, v in self.HEADERS.items():
                response[k] = v
        return response
