"""Structured draft issues must survive mixed worker/root job schemas."""

import unittest

from audit_full_pv_coverage import recorded_issues


class CoverageIssueInventoryTests(unittest.TestCase):
    def test_known_issues_with_string_static_review(self):
        self.assertEqual(recorded_issues({"static_review": "inspected",
                                          "known_issues": ["hand drift"]}), ["hand drift"])

    def test_legacy_and_current_issue_lists_merge_without_duplicates(self):
        self.assertEqual(recorded_issues({"static_review": {"flaws": ["hand", "eye"]},
                                          "known_issues": ["hand", "coat"]}),
                         ["hand", "coat", "eye"])

    def test_unstructured_notes_are_not_invented_as_flaws(self):
        self.assertEqual(recorded_issues({"static_review": "check needed"}), [])

    def test_malformed_groups_do_not_become_character_lists(self):
        self.assertEqual(recorded_issues({"known_issues": "not a list",
                                          "static_review": {"flaws": [None, "eye", 7]}}), ["eye"])


if __name__ == "__main__":
    unittest.main()
