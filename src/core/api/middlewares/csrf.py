from secrets import token_urlsafe

from fastapi import FastAPI
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

from src.core.settings import settings


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        csrf_token_name=settings.SECURITY.CSRF_COOKIE_NAME,
        csrf_token_expiry=settings.SECURITY.CSRF_EXPIRE_TIME,
    ):
        super().__init__(app)
        self.CSRF_TOKEN_NAME = csrf_token_name
        self.CSRF_TOKEN_EXPIRY = csrf_token_expiry

    async def dispatch(self, request, call_next):
        request.state.csrftoken = ""
        token_new_cookie = False

        error_text = (
            "CSRF token validation failed. "
            "The request could not be completed for security reasons. "
            "Please ensure your session is valid and try again."
        )

        token_from_header = request.headers.get(self.CSRF_TOKEN_NAME, None)
        token_from_cookie = request.cookies.get(self.CSRF_TOKEN_NAME, None)
        token_from_post = None

        if hasattr(request.state, "post"):
            token_from_post = request.state.post.get(self.CSRF_TOKEN_NAME, None)

        if request.method not in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            if (
                not token_from_cookie
                or len(token_from_cookie) < settings.SECURITY.CSRF_MIN_TOKEN_LENGTH
            ):
                logger.error("CSRF Cookie was not set. Aborting request.")
                return PlainTextResponse(error_text, status_code=403)

            if (str(token_from_cookie) != str(token_from_post)) and (
                str(token_from_cookie) != str(token_from_header)
            ):
                logger.error(
                    "Cookie: %s | Post: %s | Header: %s",
                    token_from_cookie,
                    token_from_post,
                    token_from_header,
                )

                return PlainTextResponse(error_text, status_code=403)

        elif not token_from_cookie:
            token_from_cookie = token_urlsafe(32)
            token_new_cookie = True
        else:
            token_new_cookie = False

        request.state.csrftoken = token_from_cookie
        response = await call_next(request)

        if token_new_cookie:
            logger.info("Setting up CSRF Cookie.")

            response.set_cookie(
                self.CSRF_TOKEN_NAME,
                token_from_cookie,
                max_age=self.CSRF_TOKEN_EXPIRY,
                path="/",
                domain=None,
                secure=True,
                httponly=True,
                samesite="strict",
            )

        return response
