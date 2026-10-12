import os
import tempfile
import unittest

from agentic_docuchat.persistent_memory import PersistentMemory
from agentic_docuchat.prompt_engineering import needs_grounding_repair

try:
    from agentic_docuchat.rag_backend import RagBackend
except ImportError:  # light envs without the langchain stack skip these
    RagBackend = None


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


@unittest.skipIf(RagBackend is None, "needs full backend deps (langchain stack)")
class OllamaModelErrorTests(unittest.TestCase):
    """The configured model must match an installed tag exactly — a
    same-family tag (gemma3:1b vs gemma3:4b) is a different model and
    would end in a raw server 404 instead of a helpful message."""

    def test_exact_match_is_fine(self):
        self.assertIsNone(RagBackend._ollama_model_error("gemma3:4b", ["gemma3:4b", "qwen3:1.7b"]))

    def test_same_family_suggests_installed_tag(self):
        error = RagBackend._ollama_model_error("gemma3:4b", ["gemma3:1b", "qwen3:1.7b"])
        self.assertIn("gemma3:1b", error)
        self.assertIn("ollama pull gemma3:4b", error)

    def test_no_family_suggests_pull(self):
        error = RagBackend._ollama_model_error("gemma3:4b", ["qwen3:1.7b"])
        self.assertIn("ollama pull gemma3:4b", error)
        self.assertNotIn("You have", error)


if __name__ == "__main__":
    unittest.main()
