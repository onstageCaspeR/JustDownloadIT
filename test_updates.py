import unittest

import JustDownloadIT as app


class UpdateVersionTests(unittest.TestCase):
    def test_parses_release_tags(self):
        self.assertEqual(app.parse_release_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(app.parse_release_version("1.2.3"), (1, 2, 3))
        self.assertIsNone(app.parse_release_version("latest"))
        self.assertIsNone(app.parse_release_version("v1.2"))

    def test_only_higher_versions_are_updates(self):
        self.assertTrue(app.is_newer_version("v1.2.0", "1.1.9"))
        self.assertFalse(app.is_newer_version("v1.1.0", "1.1.0"))
        self.assertFalse(app.is_newer_version("v1.0.9", "1.1.0"))

    def test_release_asset_url_is_pinned_to_official_repo(self):
        trusted = (
            "https://github.com/onstageCaspeR/JustDownloadIT/"
            "releases/download/v1.2.0/JustDownloadIT-Setup.exe"
        )
        untrusted = (
            "https://example.com/onstageCaspeR/JustDownloadIT/"
            "releases/download/v1.2.0/JustDownloadIT-Setup.exe"
        )
        spoofed_host = (
            "https://github.com.evil.example/onstageCaspeR/JustDownloadIT/"
            "releases/download/v1.2.0/JustDownloadIT-Setup.exe"
        )
        self.assertTrue(app.JustDownloadITApp._valid_release_asset_url(trusted))
        self.assertTrue(app.JustDownloadITApp._valid_release_asset_url(trusted.upper()))
        self.assertFalse(app.JustDownloadITApp._valid_release_asset_url(untrusted))
        self.assertFalse(app.JustDownloadITApp._valid_release_asset_url(spoofed_host))
        self.assertFalse(
            app.JustDownloadITApp._is_github_asset_host(
                "https://release-assets.githubusercontent.com.evil.example/file"
            )
        )


if __name__ == "__main__":
    unittest.main()
