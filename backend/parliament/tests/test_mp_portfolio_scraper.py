"""Test portfolio extraction from MP profile HTML."""
from django.test import TestCase
from parliament.services.mp_scraper import parse_parlimen_profile


class ExtractPortfolioTest(TestCase):
    def test_extracts_jawatan_from_table(self):
        """Extracts portfolio from Jawatan row in profile table."""
        html = '''
        <table>
            <tr><td>Telefon</td><td>03-1234567</td></tr>
            <tr><td>Jawatan</td><td>Menteri Pendidikan</td></tr>
            <tr><td>Email</td><td>test@parlimen.gov.my</td></tr>
        </table>
        '''
        result = parse_parlimen_profile(html)
        self.assertEqual(result["portfolio"], "Menteri Pendidikan")

    def test_returns_empty_for_backbencher(self):
        """Returns empty string for MPs without ministerial role."""
        html = '''
        <table>
            <tr><td>Telefon</td><td>03-1234567</td></tr>
            <tr><td>Email</td><td>test@parlimen.gov.my</td></tr>
        </table>
        '''
        result = parse_parlimen_profile(html)
        self.assertEqual(result["portfolio"], "")

    def test_extracts_minister_from_text(self):
        """Falls back to extracting minister title from page text."""
        html = '''
        <div>
            <p>Menteri Kewangan</p>
        </div>
        <table>
            <tr><td>Telefon</td><td>03-1234567</td></tr>
        </table>
        '''
        result = parse_parlimen_profile(html)
        self.assertEqual(result["portfolio"], "Menteri Kewangan")
