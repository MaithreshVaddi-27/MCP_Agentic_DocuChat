import os
import tempfile
import unittest

from agentic_docuchat.persistent_memory import PersistentMemory
from agentic_docuchat.prompt_engineering import needs_grounding_repair


def _temp_db():
    handle = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    handle.close()
    return handle.name


def _cleanup(db):
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.unlink(db + suffix)
        except OSError:
            pass


class CacheKeyStabilityTests(unittest.TestCase):
    """The cache key must use durable memory, not the ever-changing
    recent conversation — otherwise a repeated question never hits
    cache once any chat turn has happened."""

    def test_cache_key_is_stable_across_conversation_turns(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            user_id = "user-1"

            key_before = memory.cache_key(
                user_id, "What is RAG?", "doc-v1", "gemini:model", memory.memories_text(user_id)
            )

            # An intervening chat turn changes recent_turns_text...
            memory.add_turn(user_id, "Tell me about transformers.", "They use self-attention.")

            key_after = memory.cache_key(
                user_id, "What is RAG?", "doc-v1", "gemini:model", memory.memories_text(user_id)
            )

            self.assertEqual(key_before, key_after)
            memory.close()
        finally:
            _cleanup(db)

    def test_cache_key_changes_when_durable_memory_changes(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            user_id = "user-1"

            key_before = memory.cache_key(
                user_id, "What is RAG?", "doc-v1", "gemini:model", memory.memories_text(user_id)
            )
            memory.add_memory(user_id, "I prefer concise answers.")
            key_after = memory.cache_key(
                user_id, "What is RAG?", "doc-v1", "gemini:model", memory.memories_text(user_id)
            )

            self.assertNotEqual(key_before, key_after)
            memory.close()
        finally:
            _cleanup(db)


class GroundingRepairTests(unittest.TestCase):
    def test_short_answer_with_evidence_needs_repair(self):
        self.assertTrue(needs_grounding_repair("Yes.", "Source: paper.pdf, page 2\nSome real evidence."))

    def test_answer_without_citation_needs_repair(self):
        self.assertTrue(
            needs_grounding_repair(
                "The model uses self-attention across all positions in the sequence.",
                "Source: paper.pdf, page 2\nSome real evidence.",
            )
        )

    def test_answer_with_page_citation_does_not_need_repair(self):
        self.assertFalse(
            needs_grounding_repair(
                "According to page 2, the model uses self-attention.",
                "Source: paper.pdf, page 2\nSome real evidence.",
            )
        )

    def test_no_retrieved_context_never_needs_repair(self):
        self.assertFalse(needs_grounding_repair("Short.", "No relevant passages were found in the PDF."))


if __name__ == "__main__":
    unittest.main()
