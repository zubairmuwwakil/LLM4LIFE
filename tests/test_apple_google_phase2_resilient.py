import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apple_google_phase2 as base
import apple_google_phase2_cleanup_markers as cleanup
import apple_google_phase2_resilient as resilient


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class MarkerAfter502Session:
    def __init__(self, marker):
        self.marker = marker
        self.posts = 0
        self.gets = 0

    def post(self, *args, **kwargs):
        self.posts += 1
        return FakeResponse(502, text="temporary upstream error")

    def get(self, *args, **kwargs):
        self.gets += 1
        return FakeResponse(
            200,
            {
                "connections": [
                    {
                        "resourceName": "people/recovered",
                        "userDefined": [
                            {"key": resilient.MARKER_KEY, "value": self.marker}
                        ],
                    }
                ]
            },
        )


class NonRetryableSession:
    def __init__(self):
        self.posts = 0
        self.gets = 0

    def post(self, *args, **kwargs):
        self.posts += 1
        return FakeResponse(400, text="bad request")

    def get(self, *args, **kwargs):
        self.gets += 1
        raise AssertionError("non-retryable create must not poll/retry")


class CleanupSession:
    def __init__(self, marker):
        self.marker = marker
        self.patch_body = None

    def get(self, *args, **kwargs):
        return FakeResponse(
            200,
            {
                "resourceName": "people/x",
                "metadata": {"sources": [{"type": "CONTACT", "etag": "e1"}]},
                "userDefined": [
                    {"key": "Social: synthetic", "value": "abc"},
                    {"key": resilient.MARKER_KEY, "value": self.marker},
                ],
            },
        )

    def patch(self, *args, **kwargs):
        self.patch_body = kwargs["json"]
        return FakeResponse(200, {"resourceName": "people/x"})


class ResilientCreateTests(unittest.TestCase):
    def test_marker_is_deterministic_and_preserves_existing_user_defined(self):
        fp = "a" * 64
        body = {"userDefined": [{"key": "Social: synthetic", "value": "abc"}]}
        marked = resilient.add_marker(body, fp)
        self.assertEqual(body["userDefined"], [{"key": "Social: synthetic", "value": "abc"}])
        self.assertIn({"key": "Social: synthetic", "value": "abc"}, marked["userDefined"])
        self.assertIn(
            {"key": resilient.MARKER_KEY, "value": resilient.marker_value(fp)},
            marked["userDefined"],
        )

    @patch("apple_google_phase2_resilient.time.sleep", return_value=None)
    def test_502_recovers_marker_without_second_create(self, _sleep):
        fp = "b" * 64
        marker = resilient.marker_value(fp)
        session = MarkerAfter502Session(marker)
        body = resilient.add_marker({"names": [{"unstructuredName": "Synthetic"}]}, fp)
        result = resilient.resilient_create(session, body)
        self.assertEqual(result["resourceName"], "people/recovered")
        self.assertEqual(session.posts, 1)
        self.assertGreaterEqual(session.gets, 1)

    def test_non_retryable_400_fails_without_polling(self):
        fp = "c" * 64
        session = NonRetryableSession()
        body = resilient.add_marker({"names": [{"unstructuredName": "Synthetic"}]}, fp)
        with self.assertRaisesRegex(RuntimeError, "People create failed \(400\)"):
            resilient.resilient_create(session, body)
        self.assertEqual(session.posts, 1)
        self.assertEqual(session.gets, 0)

    def test_legacy_match_requires_more_than_same_name_alone(self):
        apple = base.AppleContact(
            ordinal=1,
            fingerprint="f",
            display_name="Synthetic Person",
            name={"unstructuredName": "Synthetic Person"},
            addresses=[{"streetAddress": "10 Main St", "city": "Toronto"}],
        )
        name_only = {"names": [{"displayName": "Synthetic Person"}]}
        rich = {
            "names": [{"displayName": "Synthetic Person"}],
            "addresses": [{"streetAddress": "10 Main St", "city": "Toronto"}],
        }
        self.assertFalse(resilient._is_safe_legacy_match(apple, name_only))
        self.assertTrue(resilient._is_safe_legacy_match(apple, rich))

    def test_cleanup_removes_only_migration_marker(self):
        fp = "d" * 64
        marker = resilient.marker_value(fp)
        session = CleanupSession(marker)
        changed = cleanup.cleanup_one(session, "people/x", marker)
        self.assertTrue(changed)
        self.assertEqual(
            session.patch_body["userDefined"],
            [{"key": "Social: synthetic", "value": "abc"}],
        )


if __name__ == "__main__":
    unittest.main()
