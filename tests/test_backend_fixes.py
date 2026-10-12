import os
import tempfile
import unittest

from agentic_docuchat.rag.memory import PersistentMemory
from agentic_docuchat.rag.prompts import needs_grounding_repair

try:
    from agentic_docuchat.rag.backend import RagBackend
except ImportError:  # light envs without the langchain stack skip these
    RagBackend = None

try:
    import agentic_docuchat.app as app_mod
except ImportError:  # light envs without gradio/full stack skip these
    app_mod = None


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

    def _bare_backend(self, **attrs):
        be = RagBackend.__new__(RagBackend)
        be._models = {}
        be._agents = {}
        for key, value in attrs.items():
            setattr(be, key, value)
        return be

    def test_drop_provider_caches_only_touches_that_provider(self):
        be = self._bare_backend()
        be._models = {"ollama:a": 1, "gemini:x": 2, "llamacpp:z": 3}
        be._agents = {"agent:ollama": 1, "agent:gemini": 2}
        be._drop_provider_caches("ollama")
        self.assertEqual(be._models, {"gemini:x": 2, "llamacpp:z": 3})
        self.assertEqual(be._agents, {"agent:gemini": 2})

    def test_set_ollama_model_offline_fails_friendly(self):
        be = self._bare_backend(
            ollama_model="gemma3:1b",
            ollama_base_url="http://localhost:11434",
        )
        be._cached_ollama_status = lambda force=False: {"running": False, "models": []}
        with self.assertRaises(RuntimeError) as ctx:
            be.set_ollama_model("qwen3:1.7b")
        self.assertIn("ollama serve", str(ctx.exception))

    def test_set_ollama_model_switches_and_drops_caches(self):
        be = self._bare_backend(
            ollama_model="gemma3:1b",
            ollama_base_url="http://localhost:11434",
        )
        be._cached_ollama_status = (
            lambda force=False: {"running": True, "models": ["gemma3:1b", "qwen3:1.7b"]}
        )
        be._models = {"ollama:gemma3:1b": object()}
        be._agents = {"agent:ollama": object()}
        self.assertIn("qwen3:1.7b", be.set_ollama_model("qwen3:1.7b"))
        self.assertEqual(be.ollama_model, "qwen3:1.7b")
        self.assertEqual(be._models, {})
        self.assertEqual(be._agents, {})

    def test_set_ollama_model_rejects_unknown_tag(self):
        be = self._bare_backend(
            ollama_model="gemma3:1b",
            ollama_base_url="http://localhost:11434",
        )
        be._cached_ollama_status = (
            lambda force=False: {"running": True, "models": ["gemma3:1b"]}
        )
        with self.assertRaises(RuntimeError) as ctx:
            be.set_ollama_model("gemma3:4b")
        self.assertIn("gemma3:1b", str(ctx.exception))

    def test_set_llamacpp_model_rejects_unreported_tag(self):
        be = self._bare_backend(
            llamacpp_model="old",
            llamacpp_base_url="http://localhost:8080/v1",
        )
        be._cached_llamacpp_status = (
            lambda force=False: {"running": True, "models": ["Qwen3"]}
        )
        with self.assertRaises(RuntimeError) as ctx:
            be.set_llamacpp_model("Other")
        self.assertIn("Qwen3", str(ctx.exception))


@unittest.skipIf(app_mod is None, "needs gradio + full backend deps")
class UploadUiTests(unittest.TestCase):
    def test_quick_check_rejects_wrong_extension(self):
        handle = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        handle.write(b"hello")
        handle.close()
        try:
            self.assertIn(".pdf", app_mod._quick_pdf_check(handle.name))
        finally:
            os.unlink(handle.name)

    def test_quick_check_rejects_fake_pdf_instantly(self):
        handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        handle.write(b"plain text, not a pdf")
        handle.close()
        try:
            self.assertIn("%PDF", app_mod._quick_pdf_check(handle.name))
        finally:
            os.unlink(handle.name)

    def test_quick_check_accepts_real_header(self):
        handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        handle.write(b"%PDF-1.4 fake but headered")
        handle.close()
        try:
            self.assertIsNone(app_mod._quick_pdf_check(handle.name))
        finally:
            os.unlink(handle.name)

    def test_banner_shows_setup_error_and_clears(self):
        app_mod.startup_error = "boom"
        try:
            self.assertIn("boom", app_mod._banner_text())
        finally:
            app_mod.startup_error = ""
        self.assertEqual(app_mod._banner_text(), "")

    def test_fake_upload_fails_fast_without_backend(self):
        app_mod.backend = None
        handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        handle.write(b"plain text, not a pdf")
        handle.close()
        try:
            import asyncio

            yields = list(asyncio.run(_collect(app_mod.upload_document(handle.name))))
            self.assertEqual(len(yields), 1)  # single instant failure, no backend init
            self.assertIn("%PDF", yields[0][0])
            self.assertEqual(len(yields[0]), 4)  # message, status, banner, models
        finally:
            os.unlink(handle.name)

    def test_select_model_without_backend_reports_setup(self):
        app_mod.backend = None
        app_mod.startup_error = "boom"
        try:
            self.assertIn("boom", app_mod.select_model("Ollama", "gemma3:1b"))
        finally:
            app_mod.startup_error = ""

    def test_select_model_for_gemini_points_at_env(self):
        old_backend = app_mod.backend
        app_mod.backend = object()  # any non-None backend; Gemini path never touches it
        try:
            self.assertIn("GEMINI_MODEL", app_mod.select_model("Gemini", "gemini-3.5-flash-lite"))
        finally:
            app_mod.backend = old_backend

    def test_provider_key_normalizes_labels(self):
        self.assertEqual(app_mod._provider_key("Llama.cpp"), "llamacpp")
        self.assertEqual(app_mod._provider_key("Ollama"), "ollama")
        self.assertEqual(app_mod._provider_key("Gemini"), "gemini")

    def _ns(self, share=False, no_share=False):
        import types

        return types.SimpleNamespace(share=share, no_share=no_share)

    def _resolve(self, env, **flags):
        from unittest import mock

        with mock.patch.dict(os.environ, env, clear=False):
            return app_mod._resolve_share_auth(self._ns(**flags))

    def test_share_off_no_creds_is_open_local(self):
        env = {"GRADIO_SHARE": "false", "GRADIO_USERNAME": "", "GRADIO_PASSWORD": ""}
        self.assertEqual(self._resolve(env), (False, None))

    def test_credentials_protect_even_without_share(self):
        env = {"GRADIO_SHARE": "false", "GRADIO_USERNAME": "me", "GRADIO_PASSWORD": "s3cret"}
        self.assertEqual(self._resolve(env), (False, ("me", "s3cret")))

    def test_share_without_credentials_refuses(self):
        env = {"GRADIO_SHARE": "true", "GRADIO_USERNAME": "", "GRADIO_PASSWORD": ""}
        with self.assertRaises(RuntimeError):
            self._resolve(env)

    def test_share_with_credentials_allowed(self):
        env = {"GRADIO_SHARE": "true", "GRADIO_USERNAME": "me", "GRADIO_PASSWORD": "s3cret"}
        self.assertEqual(self._resolve(env), (True, ("me", "s3cret")))

    def test_placeholder_credentials_mean_no_auth(self):
        env = {
            "GRADIO_SHARE": "false",
            "GRADIO_USERNAME": "choose_a_username",
            "GRADIO_PASSWORD": "choose_a_strong_password",
        }
        self.assertEqual(self._resolve(env), (False, None))

    def test_cli_flags_override_env(self):
        env = {"GRADIO_SHARE": "true", "GRADIO_USERNAME": "me", "GRADIO_PASSWORD": "s3cret"}
        self.assertEqual(self._resolve(env, no_share=True), (False, ("me", "s3cret")))


async def _collect(gen):
    return [item async for item in gen]


if __name__ == "__main__":
    unittest.main()
