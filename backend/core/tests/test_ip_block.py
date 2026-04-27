"""Tests for IPBlockMiddleware (Sprint 17 — Egress Hardening)."""

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from core.middleware import IPBlockMiddleware


def _ok(_request):
    return HttpResponse(b"ok")


class IPBlockMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = IPBlockMiddleware(_ok)

    def test_blocks_known_scraper_ip_via_cf_connecting_ip(self):
        request = self.factory.get("/", HTTP_CF_CONNECTING_IP="88.216.210.27")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_blocks_known_scraper_ip_via_x_forwarded_for(self):
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="88.216.210.27")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_blocks_known_scraper_ip_via_xff_first_hop(self):
        # Cloudflare prepends real IP, then proxy hops follow.
        request = self.factory.get(
            "/", HTTP_X_FORWARDED_FOR="88.216.210.27, 10.0.0.1, 10.0.0.2"
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_allows_unknown_ip(self):
        request = self.factory.get("/", HTTP_CF_CONNECTING_IP="203.0.113.1")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_allows_request_with_no_ip_headers(self):
        # REMOTE_ADDR alone (direct test client). Should not 403.
        request = self.factory.get("/")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_cf_header_takes_priority_over_xff(self):
        # If Cloudflare says the client is allowed but XFF was forged with a
        # blocked IP, trust Cloudflare's header (added by our trusted proxy).
        request = self.factory.get(
            "/",
            HTTP_CF_CONNECTING_IP="203.0.113.1",
            HTTP_X_FORWARDED_FOR="88.216.210.27",
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
