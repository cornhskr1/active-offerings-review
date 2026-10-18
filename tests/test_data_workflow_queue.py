"""Offline guardrails for GitHub's shared generated-data writer queue."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
SHARED_WRITERS = (
    'refresh-competition-identity-registry.yml',
    'refresh-data.yml',
    'refresh-global-schedule.yml',
    'refresh-ncaa-basketball-age-cache.yml',
    'refresh-ncaa-basketball-rosters.yml',
    'refresh-ncaa-basketball.yml',
    'refresh-ncaa-football.yml',
    'refresh-nebraska-collegiate.yml',
    'refresh-priority-queue.yml',
    'refresh-tennis-review.yml',
    'research-ncaa-basketball-ages.yml',
)


class DataWorkflowQueueTests(unittest.TestCase):
    def test_existing_writers_keep_the_shared_workflow_level_lock(self):
        for name in SHARED_WRITERS:
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text()
                block = re.search(r'^concurrency:\n((?:[ \t]+[^\n]*\n|\n)+)', text, re.M)
                self.assertIsNotNone(block, 'Keep serialization around the whole refresh, not only publication')
                self.assertRegex(block.group(1), r'(?m)^  group: active-offerings-data$')
                self.assertRegex(block.group(1), r'(?m)^  cancel-in-progress: false$')

    def test_every_shared_queue_member_preserves_pending_runs(self):
        # Check new members too: a member left on the default single-slot queue
        # can reintroduce pending-run replacement in the shared writer group.
        members = []
        for path in WORKFLOWS.glob('*.yml'):
            text = path.read_text()
            if 'group: active-offerings-data' not in text:
                continue
            members.append(path.name)
            with self.subTest(workflow=path.name):
                block = re.search(r'^concurrency:\n((?:[ \t]+[^\n]*\n|\n)+)', text, re.M)
                self.assertIsNotNone(block)
                self.assertRegex(block.group(1), r'(?m)^  queue: max$')
                self.assertRegex(block.group(1), r'(?m)^  cancel-in-progress: false$')
        self.assertTrue(set(SHARED_WRITERS).issubset(members))

    def test_queued_writers_sync_current_main_before_generation_and_rebase_before_push(self):
        for name in SHARED_WRITERS:
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text()
                sync = text.index('git reset --hard origin/main')
                generation = text.index('run: python3')
                commit = text.index('git commit ')
                rebase = text.index('git rebase origin/main')
                push = text.index('git push origin HEAD:main')
                self.assertLess(text.index('git fetch origin main'), sync)
                self.assertLess(sync, generation)
                self.assertLess(generation, commit)
                self.assertLess(commit, rebase)
                self.assertLess(rebase, push)
                self.assertNotIn('git push --force', text)


if __name__ == '__main__':
    unittest.main()
