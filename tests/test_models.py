from __future__ import annotations

import unittest

from src.collect.models import AccountRef


class AccountRefNormalizationTest(unittest.TestCase):
    def test_instagram_username_strips_zero_width_and_at_sign(self) -> None:
        account = AccountRef(platform="instagram", username="\u200b\u200b@grandma_droniak")

        self.assertEqual(account.username, "grandma_droniak")
        self.assertIsNone(account.user_id)
        self.assertEqual(account.to_params(), {"username": "grandma_droniak"})

    def test_instagram_handle_in_user_id_is_promoted_to_username(self) -> None:
        account = AccountRef(platform="instagram", user_id="\u200b\u200b@grandma_droniak")

        self.assertEqual(account.username, "grandma_droniak")
        self.assertIsNone(account.user_id)
        self.assertEqual(account.to_params(), {"username": "grandma_droniak"})

    def test_instagram_numeric_user_id_is_preserved(self) -> None:
        account = AccountRef(platform="instagram", user_id=" 1234567890 ")

        self.assertIsNone(account.username)
        self.assertEqual(account.user_id, "1234567890")
        self.assertEqual(account.to_params(), {"user_id": "1234567890"})


if __name__ == "__main__":
    unittest.main()
