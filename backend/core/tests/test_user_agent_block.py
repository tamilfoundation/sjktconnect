"""Tests for UserAgentBlockMiddleware (Sprint 21 — Egress Hardening Round 2)."""

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from core.middleware import UserAgentBlockMiddleware


def _ok(_request):
    return HttpResponse(b"ok")


class UserAgentBlockMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = UserAgentBlockMiddleware(_ok)

    def test_blocks_awariobot(self):
        request = self.factory.get("/", HTTP_USER_AGENT="AwarioBot/1.0")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_blocks_semrushbot(self):
        request = self.factory.get(
            "/", HTTP_USER_AGENT="Mozilla/5.0 (compatible; SemrushBot/7~bl)"
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_blocks_dataforseobot(self):
        request = self.factory.get(
            "/", HTTP_USER_AGENT="Mozilla/5.0 (compatible; DataForSeoBot/1.0)"
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_match_is_case_insensitive(self):
        request = self.factory.get("/", HTTP_USER_AGENT="awariobot")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_allows_real_browser_user_agent(self):
        request = self.factory.get(
            "/",
            HTTP_USER_AGENT=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_allows_request_with_no_user_agent(self):
        request = self.factory.get("/")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_allows_legit_search_engine(self):
        request = self.factory.get(
            "/",
            HTTP_USER_AGENT=(
                "Mozilla/5.0 (compatible; Googlebot/2.1; "
                "+http://www.google.com/bot.html)"
            ),
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
