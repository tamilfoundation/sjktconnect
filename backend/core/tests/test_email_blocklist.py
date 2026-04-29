"""Tests for the email-domain blocklist (Sprint 22 hotfix)."""

from django.test import TestCase

from core.email_blocklist import is_blocked_email


class IsBlockedEmailTests(TestCase):
    def test_blocks_example_com(self):
        self.assertTrue(is_blocked_email("test@example.com"))
        self.assertTrue(is_blocked_email("reader@example.com"))

    def test_blocks_example_org_and_net(self):
        self.assertTrue(is_blocked_email("foo@example.org"))
        self.assertTrue(is_blocked_email("bar@example.net"))

    def test_blocks_disposable_domains(self):
        self.assertTrue(is_blocked_email("foo@mailinator.com"))
        self.assertTrue(is_blocked_email("foo@10minutemail.com"))
        self.assertTrue(is_blocked_email("foo@yopmail.com"))

    def test_blocks_reserved_tld_suffixes(self):
        self.assertTrue(is_blocked_email("admin@my.local"))
        self.assertTrue(is_blocked_email("foo@bar.invalid"))
        self.assertTrue(is_blocked_email("foo@dev.test"))
        self.assertTrue(is_blocked_email("user@host.localhost"))

    def test_match_is_case_insensitive(self):
        self.assertTrue(is_blocked_email("TEST@Example.COM"))
        self.assertTrue(is_blocked_email("Foo@MAILINATOR.com"))

    def test_strips_whitespace(self):
        self.assertTrue(is_blocked_email("  test@example.com  "))

    def test_allows_real_domains(self):
        self.assertFalse(is_blocked_email("user@gmail.com"))
        self.assertFalse(is_blocked_email("admin@tamilfoundation.org"))
        self.assertFalse(is_blocked_email("teacher@moe.edu.my"))
        # examples-look-like-but-aren't:
        self.assertFalse(is_blocked_email("foo@notexample.com"))
        self.assertFalse(is_blocked_email("foo@example.com.attacker.com"))

    def test_handles_empty_or_malformed(self):
        self.assertFalse(is_blocked_email(""))
        self.assertFalse(is_blocked_email("notanemail"))
        self.assertFalse(is_blocked_email("@nodomain"))
        self.assertFalse(is_blocked_email(None) if hasattr(__builtins__, '__contains__') else False)
