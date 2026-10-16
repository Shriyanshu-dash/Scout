"""Offline regression tests for multi-profile CSV export."""

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scout as cli


class CSVExportTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [
            {
                "username": "alpha",
                "platform": "github",
                "full_name": "Alpha",
            },
            {
                "username": "beta",
                "platform": "github",
                "bio": "Beta profile",
                "follower_count": 12,
            },
        ]

    def test_fieldnames_include_union_in_stable_order(self):
        self.assertEqual(
            cli._csv_fieldnames(self.profiles),
            [
                "username",
                "platform",
                "full_name",
                "bio",
                "follower_count",
            ],
        )

    def test_export_handles_profiles_with_different_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)

                with (
                    patch.object(
                        cli, "enrich_profiles", side_effect=lambda p: p
                    ),
                    patch.object(cli.Confirm, "ask", return_value=True),
                    patch.object(cli, "_success_summary"),
                    patch.object(cli, "_export_result"),
                    patch.object(
                        cli.time,
                        "strftime",
                        return_value="20261017_010101",
                    ),
                ):
                    cli._standard_export(
                        self.profiles, 2, "github"
                    )
            finally:
                os.chdir(old_cwd)

            path = Path(tmp) / "github_export_20261017_010101.csv"
            self.assertTrue(path.exists())

            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                columns = reader.fieldnames

            self.assertEqual(
                columns,
                [
                    "username",
                    "platform",
                    "full_name",
                    "bio",
                    "follower_count",
                ],
            )
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["username"], "alpha")
            self.assertEqual(rows[0]["bio"], "")
            self.assertEqual(rows[1]["username"], "beta")
            self.assertEqual(rows[1]["full_name"], "")
            self.assertEqual(rows[1]["follower_count"], "12")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(
        __import__(__name__, fromlist=["*"])
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
