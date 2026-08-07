from app.providers.resend_provider import ResendProvider


def get_email_provider():
    return ResendProvider()
