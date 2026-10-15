import os
import sqlite3
import tempfile
import unittest
from unittest import mock

import agentic_docuchat.rag.memory as memory_module
from agentic_docuchat.rag.memory import PersistentMemory, ResponseCache


def _temp_db():
    """Windows-safe temp DB: NamedTemporaryFile avoids locked-dir cleanup."""
    handle = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    handle.close()
    return handle.name


def _cleanup(db):
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.unlink(db + suffix)
        except OSError:
            pass


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
            _cleanup(db)

    def test_personal_fact_is_captured_without_a_memory_name(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            captured = memory.auto_capture("user-1", "I prefer concise answers.")

            self.assertIsNotNone(captured)
            self.assertIn("concise answers", memory.memories("user-1")[0])
            memory.close()
        finally:
            _cleanup(db)


class ConnectionLifecycleTests(unittest.TestCase):
    """Every operation must hand back its connection.

    sqlite3's `with connection:` ends the transaction but leaves the handle
    open, so a long-running server would slowly run out of file descriptors.
    """

    def _record_connections(self, memory):
        """Spy on every connection the store opens during the block."""
        opened = []
        real_connect = sqlite3.connect

        def spy(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            opened.append(connection)
            return connection

        return mock.patch.object(memory_module.sqlite3, "connect", spy), opened

    def _assert_closed(self, connection):
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")

    def test_write_releases_its_connection(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            patcher, opened = self._record_connections(memory)
            with patcher:
                memory.add_turn("user-1", "q", "a")
            self._assert_closed(opened[-1])
            memory.close()
        finally:
            _cleanup(db)

    def test_read_releases_its_connection(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            memory.add_turn("user-1", "q", "a")
            patcher, opened = self._record_connections(memory)
            with patcher:
                self.assertEqual(len(memory.recent_turns("user-1")), 1)
            self._assert_closed(opened[-1])
            memory.close()
        finally:
            _cleanup(db)

    def test_failed_operation_releases_and_rolls_back(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            patcher, opened = self._record_connections(memory)
            with patcher:
                with self.assertRaises(sqlite3.OperationalError):
                    with memory._connect() as connection:
                        connection.execute("SELECT * FROM table_that_does_not_exist")
            self._assert_closed(opened[-1])
            # Still usable afterwards: the connection was rolled back and
            # released rather than left poisoned.
            memory.add_turn("user-1", "q", "a")
            self.assertEqual(len(memory.recent_turns("user-1")), 1)
            memory.close()
        finally:
            _cleanup(db)

    def test_cache_operations_release_their_connection(self):
        db = _temp_db()
        try:
            memory = PersistentMemory(db)
            cache = ResponseCache(memory)
            patcher, opened = self._record_connections(memory)
            with patcher:
                cache.put("key", {"answer": "a"})
                cache.get("key")
                cache.clear()
            for connection in opened:
                self._assert_closed(connection)
            self.assertGreaterEqual(len(opened), 3)
            memory.close()
        finally:
            _cleanup(db)


if __name__ == "__main__":
    unittest.main()
