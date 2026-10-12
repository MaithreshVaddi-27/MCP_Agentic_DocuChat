import os
import tempfile
import unittest

from agentic_docuchat.rag.memory import PersistentMemory, ResponseCache


def _temp_db():
    """Windows-safe temp DB: NamedTemporaryFile avoids locked-dir cleanup."""
    handle = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    handle.close()
    return handle.name


class PersistentMemoryTests(unittest.TestCase):
    def test_memory_turns_and_cache_survive_store_use(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            memory.add_memory("user-1", "I prefer short explanations.")
            memory.add_turn("user-1", "What is RAG?", "RAG combines retrieval and generation.")
            cache = ResponseCache(memory)
            cache.put("question-key", {"answer": "cached answer"})

            self.assertIn("short explanations", memory.context("user-1"))
            self.assertEqual(memory.recent_turns("user-1")[0]["question"], "What is RAG?")
            self.assertEqual(cache.get("question-key")["answer"], "cached answer")
            memory.close()
        finally:
            for suffix in ("", "-wal", "-shm", "-journal"):
                try:
                    os.unlink(db + suffix)
                except OSError:
                    pass

    def test_personal_fact_is_captured_without_a_memory_name(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            captured = memory.auto_capture("user-1", "I prefer concise answers.")

            self.assertIsNotNone(captured)
            self.assertIn("concise answers", memory.memories("user-1")[0])
            memory.close()
        finally:
            for suffix in ("", "-wal", "-shm", "-journal"):
                try:
                    os.unlink(db + suffix)
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
