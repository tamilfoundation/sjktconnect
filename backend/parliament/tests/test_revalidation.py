"""Tests for Parliament Watch ISR revalidation on brief publish."""

from unittest.mock import MagicMock, patch

from parliament.services.revalidation import trigger_brief_revalidate


def _brief(pk=142):
    b = MagicMock()
    b.id = pk
    return b


def test_posts_parliament_payload_with_token():
    with patch.dict("os.environ", {
        "REVALIDATE_WEBHOOK_URL": "https://tamilschool.org/api/revalidate",
        "REVALIDATE_TOKEN": "secret-tok",
    }), patch("parliament.services.revalidation.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        trigger_brief_revalidate(_brief(142))

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {"type": "parliament", "key": "142"}
    assert kwargs["headers"]["X-Revalidate-Token"] == "secret-tok"


def test_noop_when_env_unset():
    with patch.dict("os.environ", {}, clear=True), \
         patch("parliament.services.revalidation.requests.post") as mock_post:
        trigger_brief_revalidate(_brief())
    mock_post.assert_not_called()


def test_swallows_network_errors():
    with patch.dict("os.environ", {
        "REVALIDATE_WEBHOOK_URL": "https://x/api/revalidate",
        "REVALIDATE_TOKEN": "t",
    }), patch("parliament.services.revalidation.requests.post",
              side_effect=Exception("boom")):
        # Must not raise — revalidation failure can't block the publish.
        trigger_brief_revalidate(_brief())
