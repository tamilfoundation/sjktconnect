import pytest
from django.test import TestCase

from parliament.models import MP
from schools.models import Constituency


@pytest.mark.django_db
class MPModelTests(TestCase):
    """Tests for the MP model."""

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P078",
            name="Sungai Siput",
            state="Perak",
        )

    def test_create_mp_with_required_fields(self):
        """MP can be created with just constituency and name."""
        mp = MP.objects.create(
            constituency=self.constituency,
            name="Dr. Kesavan Subramaniam",
        )
        assert mp.pk is not None
        assert mp.name == "Dr. Kesavan Subramaniam"
        assert mp.constituency == self.constituency

    def test_onetoone_reverse_access(self):
        """Constituency can access its MP via reverse relation."""
        mp = MP.objects.create(
            constituency=self.constituency,
            name="Dr. Kesavan Subramaniam",
        )
        assert self.constituency.mp == mp

    def test_nullable_fields_default_to_none(self):
        """Optional contact fields default to None/empty."""
        mp = MP.objects.create(
            constituency=self.constituency,
            name="Dr. Kesavan Subramaniam",
        )
        assert mp.email is None
        assert mp.phone is None
        assert mp.fax is None
        assert mp.facebook_url is None
        assert mp.twitter_url is None
        assert mp.instagram_url is None
        assert mp.website_url is None
        assert mp.service_centre_address is None
        assert mp.photo_url == ""
        assert mp.party == ""

    def test_parlimen_profile_url_with_id(self):
        """parlimen_profile_url returns correct URL when ID is set."""
        mp = MP.objects.create(
            constituency=self.constituency,
            name="Dr. Kesavan Subramaniam",
            parlimen_profile_id="1234",
        )
        assert mp.parlimen_profile_url == (
            "https://www.parlimen.gov.my/profile-ahli.html?uweb=dr&id=1234"
        )

    def test_mymp_profile_url_with_slug(self):
        """mymp_profile_url returns correct URL when slug is set."""
        mp = MP.objects.create(
            constituency=self.constituency,
            name="Dr. Kesavan Subramaniam",
            mymp_slug="kesavan-subramaniam",
        )
        assert mp.mymp_profile_url == (
            "https://mymp.org.my/p/kesavan-subramaniam"
        )

    def test_empty_profile_urls_return_none(self):
        """Profile URLs return None when IDs are empty."""
        mp = MP.objects.create(
            constituency=self.constituency,
            name="Dr. Kesavan Subramaniam",
        )
        assert mp.parlimen_profile_url is None
        assert mp.mymp_profile_url is None

    def test_str_representation(self):
        """__str__ returns name and constituency code."""
        mp = MP.objects.create(
            constituency=self.constituency,
            name="Dr. Kesavan Subramaniam",
        )
        assert str(mp) == "Dr. Kesavan Subramaniam (P078)"
