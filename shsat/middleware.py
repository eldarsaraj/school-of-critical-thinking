from django.shortcuts import redirect
from django.urls import resolve, Resolver404

# SHSAT URL names that don't require email verification
_EXEMPT = {
    "shsat_signup",
    "shsat_login",
    "shsat_logout",
    "shsat_landing",
    "shsat_resources",
    "shsat_terms",
    "shsat_verify_pending",
    "shsat_verify_email",
    "shsat_verify_resend",
    "shsat_stripe_webhook",
}


class EmailVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            try:
                url_name = resolve(request.path_info).url_name
            except Resolver404:
                url_name = None

            if url_name and url_name.startswith("shsat_") and url_name not in _EXEMPT:
                try:
                    parent = request.user.shsat_profile
                    if not parent.email_verified:
                        return redirect("shsat_verify_pending")
                except Exception:
                    pass

        return self.get_response(request)
