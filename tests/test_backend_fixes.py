import os
import tempfile
import unittest
from unittest import mock

from agentic_docuchat.rag.backend import EMPTY_ANSWER_NOTICE
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
class BootsWithoutADocumentTests(unittest.TestCase):
    """PDFs are uploaded through the UI, so 'no document yet' is the normal
    startup state. It must not take the app down — a fresh clone has no
    data/*.pdf because they are git-ignored, and every control in the UI has
    to work before the first upload."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _backend(self, **overrides):
        from unittest import mock

        env = {
            "MEMORY_DATABASE": os.path.join(self.tmp.name, "memory.sqlite3"),
            "CHROMA_DIR": os.path.join(self.tmp.name, "chroma"),
            "RATE_LIMIT_SECONDS": "0",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            backend = RagBackend(**overrides)
        self.addCleanup(backend.memory.close)
        return backend

    def test_construction_succeeds_with_no_document(self):
        be = self._backend()
        self.assertFalse(be.document_ready)
        self.assertEqual(be.documents, [])
        self.assertIsNone(be.vector_store)
        self.assertEqual(be.document_error, "")

    def test_construction_succeeds_with_a_missing_path(self):
        be = self._backend(document_path="/definitely/not/here.pdf")
        self.assertFalse(be.document_ready)
        self.assertIn("couldn't find", be.document_error)

    def test_asking_without_a_document_returns_a_next_step(self):
        import asyncio

        be = self._backend()
        result = asyncio.run(be.ask("anything?"))
        self.assertEqual(result["sources"], [])
        self.assertIn("Upload a PDF", result["answer"])

    def test_missing_path_says_what_is_wrong(self):
        import asyncio

        be = self._backend(document_path="/definitely/not/here.pdf")
        self.assertEqual(asyncio.run(be.ask("anything?"))["sources"], [])

    def test_status_reports_readiness(self):
        be = self._backend()
        status = be.status(refresh=False)
        self.assertFalse(status["document_ready"])
        self.assertEqual(status["pages"], 0)

    def test_failed_upload_keeps_the_previous_document(self):
        """One bad PDF must not leave the app pointed at a file it cannot read."""
        be = self._backend()
        be.document_path = "good.pdf"
        be.document_ready = True
        be.documents = ["page"]
        be.vector_store = object()
        be._refresh_index = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("bad pdf"))
        with self.assertRaises(RuntimeError):
            be.load_document("broken.pdf")
        self.assertEqual(be.document_path, "good.pdf")


@unittest.skipIf(RagBackend is None, "needs full backend deps (langchain stack)")
class VectorStoreLifecycleTests(unittest.TestCase):
    """One collection per (document, embedding space), reused on rebuild.

    Every rebuild used to mint a new suffixed collection name, so the vector
    store grew by one full copy of the document per rebuild — three superseded
    copies were sitting on disk."""

    def _bare_backend(self, **attrs):
        be = RagBackend.__new__(RagBackend)
        be.embedding_provider = "local"
        be.embedding_model_name = "BAAI/bge-base-en-v1.5"
        be.embedding_model_online = "models/text-embedding-004"
        be.document_path = None
        for key, value in attrs.items():
            setattr(be, key, value)
        return be

    def test_collection_name_is_derived_not_minted(self):
        be = self._bare_backend()
        first = be._collection_name("fingerprint-a")
        self.assertEqual(first, be._collection_name("fingerprint-a"))

    def test_different_documents_get_different_collections(self):
        be = self._bare_backend()
        self.assertNotEqual(be._collection_name("a"), be._collection_name("b"))

    def test_collection_is_namespaced_by_config(self):
        be = self._bare_backend()
        with mock.patch.dict(os.environ, {"CHROMA_COLLECTION": "my_corpus"}, clear=False):
            self.assertTrue(be._collection_name("a").startswith("my_corpus_"))

    def test_sweep_removes_only_our_superseded_collections(self):
        be = self._bare_backend()
        removed = []

        class FakeCollection:
            def __init__(self, name):
                self.name = name

        class FakeClient:
            def list_collections(self):
                return [
                    FakeCollection("agentic_rag_research_collection_keep"),
                    FakeCollection("agentic_rag_research_collection_stale"),
                    FakeCollection("someone_elses_unrelated_collection"),
                ]

            def delete_collection(self, name):
                removed.append(name)

        be._client = lambda: FakeClient()
        with mock.patch.dict(
            os.environ, {"CHROMA_COLLECTION": "agentic_rag_research_collection"}, clear=False
        ):
            be._sweep_collections(keep="agentic_rag_research_collection_keep")
        self.assertEqual(removed, ["agentic_rag_research_collection_stale"])

    def test_sweep_survives_a_broken_client(self):
        be = self._bare_backend()

        class BrokenClient:
            def list_collections(self):
                raise RuntimeError("chroma is unhappy")

        be._client = lambda: BrokenClient()
        be._sweep_collections(keep="whatever")  # must not raise


@unittest.skipIf(RagBackend is None, "needs full backend deps (langchain stack)")
class RateLimitMapTests(unittest.TestCase):
    """user_id is free text from a textbox, so the cooldown map would grow
    without bound on a long-running server."""

    def _backend(self):
        be = RagBackend.__new__(RagBackend)
        be.rate_limit_seconds = 0
        be.rate_limit_max_users = 16
        be._last_request_time = {}
        return be

    def test_map_stays_bounded(self):
        be = self._backend()
        for index in range(500):
            be._check_rate_limit(f"user-{index}")
        self.assertLessEqual(len(be._last_request_time), be.rate_limit_max_users)

    def test_recent_user_is_not_evicted(self):
        be = self._backend()
        for index in range(200):
            be._check_rate_limit(f"user-{index}")
        be._check_rate_limit("the-one-that-just-asked")
        self.assertIn("the-one-that-just-asked", be._last_request_time)

    def test_cooldown_still_blocks_a_fast_repeat(self):
        be = self._backend()
        be.rate_limit_seconds = 30
        be._check_rate_limit("alice")
        with self.assertRaises(RuntimeError) as ctx:
            be._check_rate_limit("alice")
        self.assertIn("wait", str(ctx.exception))


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

    def test_set_mlx_model_offline_fails_friendly(self):
        be = self._bare_backend(
            mlx_model="mlx-community/gemma-3-4b-it-4bit",
            mlx_base_url="http://localhost:8081/v1",
        )
        be._cached_mlx_status = lambda force=False: {"running": False, "models": []}
        with self.assertRaises(RuntimeError) as ctx:
            be.set_mlx_model("other")
        self.assertIn("mlx_lm.server", str(ctx.exception))

    def test_set_mlx_model_switches_and_drops_caches(self):
        be = self._bare_backend(
            mlx_model="old-model",
            mlx_base_url="http://localhost:8081/v1",
        )
        be._cached_mlx_status = (
            lambda force=False: {"running": True, "models": ["new-model"]}
        )
        be._models = {"mlx:old-model": object()}
        be._agents = {"agent:mlx": object()}
        self.assertIn("new-model", be.set_mlx_model("new-model"))
        self.assertEqual(be.mlx_model, "new-model")
        self.assertEqual(be._models, {})
        self.assertEqual(be._agents, {})


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

    def test_upload_from_the_upload_dir_does_not_copy_a_file_onto_itself(self):
        """A PDF already in data/uploads resolves to the destination.

        Gradio passes a temp path, so the copy normally has a source and a
        destination that differ — but the README tells people to keep their
        PDFs in data/uploads, and copy2 refuses to copy a file onto itself.
        """
        import asyncio
        import pathlib

        app_mod.backend = mock.Mock()
        app_mod.backend.load_document.return_value = "Backend is ready."
        uploads = pathlib.Path("data/uploads")
        uploads.mkdir(parents=True, exist_ok=True)
        already_there = uploads / "already-there.pdf"
        already_there.write_bytes(b"%PDF-1.4 fake")
        try:
            yields = list(asyncio.run(_collect(app_mod.upload_document(str(already_there)))))
            self.assertNotIn("SameFileError", yields[-1][0])
            self.assertNotIn("same file", yields[-1][0])
            app_mod.backend.load_document.assert_called_once()
        finally:
            already_there.unlink(missing_ok=True)

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

    def test_status_line_flags_a_model_the_server_does_not_serve(self):
        """A green dot beside a model that is not installed only becomes a 404
        on the user's first question — say so up front."""
        line = app_mod._provider_line(
            "Ollama", "ollama", {"running": True, "models": ["qwen3:1.7b"]}, "gemma3:4b"
        )
        self.assertIn("running", line)
        self.assertIn("not installed", line)

    def test_status_line_is_quiet_when_the_model_is_served(self):
        line = app_mod._provider_line(
            "Ollama", "ollama", {"running": True, "models": ["gemma3:4b"]}, "gemma3:4b"
        )
        self.assertIn("running", line)
        self.assertNotIn("not installed", line)

    def test_offline_line_reports_models_waiting_on_disk(self):
        line = app_mod._provider_line(
            "MLX", "mlx", {"running": False, "models_on_disk": ["org/a-mlx", "org/b-mlx"]}, "x"
        )
        self.assertIn("offline", line)
        self.assertIn("2 model(s) on disk", line)
        self.assertIn("mlx_lm.server", line)

    def test_offline_line_without_models_stays_short(self):
        line = app_mod._provider_line("MLX", "mlx", {"running": False, "models_on_disk": []}, "x")
        self.assertIn("offline", line)
        self.assertNotIn("on disk", line)

    def test_status_text_asks_for_an_upload_before_one_exists(self):
        old = app_mod.backend
        stub = mock.MagicMock()
        stub.status.return_value = {
            "document": "(none)",
            "document_ready": False,
            "document_error": "",
            "pages": 0,
            "embedding_model": "bge (local)",
            "mcp_tools": "off",
            "ollama_model": "gemma3:4b",
            "llamacpp_model": "q",
            "mlx_model": "m",
            "ollama": {"running": True, "models": ["gemma3:4b"], "models_on_disk": []},
            "llamacpp": {"running": False, "models": [], "models_on_disk": []},
            "mlx": {"running": False, "models": [], "models_on_disk": []},
        }
        app_mod.backend = stub
        try:
            text = app_mod._status_text()
            self.assertIn("No document loaded", text)
            self.assertIn("upload a PDF", text)
        finally:
            app_mod.backend = old

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


class StreamingYieldsTheFinalAnswerTests(unittest.TestCase):
    """astream_answer must hand back the finished answer, not just chunks.

    Anything computed after the stream — a grounding-repair rewrite, or the
    empty-answer notice — was cached but never yielded, so the UI kept showing
    the last streamed chunk. Found live against a reasoning model on MLX that
    streams thousands of empty chunks.
    """

    def _backend(self, pieces, repair="Repaired: page 1 says X."):
        import asyncio

        from agentic_docuchat.rag import backend as backend_mod

        instance = object.__new__(backend_mod.RagBackend)
        instance.document_ready = True
        instance.document_version = "v1"
        instance.retrieval_k = 4
        instance.retrieval_fetch_k = 12
        instance._last_request_time = {}
        instance.rate_limit_seconds = 0
        instance.rate_limit_max_users = 1024
        instance.memory = mock.Mock()
        instance.memory.cache_key.return_value = "k"
        instance.memory.recent_turns_text.return_value = ""
        instance.memory.memories_text.return_value = ""
        instance.cache = mock.Mock()
        instance.cache.get.return_value = None
        instance._models = {}
        instance._agents = {}

        class FakeModel:
            async def astream(self, _prompt):
                for piece in pieces:
                    yield mock.Mock(content=piece)

            async def ainvoke(self, *_a, **_k):
                return mock.Mock(content=repair)

        instance._retrieve = lambda q, k=None, fetch_k=None: ("CTX", ["doc.pdf — page 1"], [])
        instance._get_model = lambda provider: (FakeModel(), "fake-model")
        instance._use_agent = lambda provider: False
        return instance, asyncio

    def _collect(self, instance, question="q", user="u", provider="llamacpp", repair_needed=False):
        """Drain the stream. `repair_needed` decides whether the grounding
        check fires, so tests that are not about repair are not rewritten."""
        import asyncio

        async def run():
            with mock.patch(
                "agentic_docuchat.rag.backend.needs_grounding_repair",
                return_value=repair_needed,
            ):
                return [item async for item in instance.astream_answer(question, user, provider)]

        return asyncio.run(run())

    def test_last_yield_is_the_complete_answer(self):
        instance, _ = self._backend(["Hel", "lo ", "world"])
        yields = self._collect(instance)
        self.assertEqual(yields[-1][0], "Hello world")

    def test_empty_stream_ends_with_an_explanation_not_a_blank(self):
        instance, _ = self._backend(["", "", ""])
        yields = self._collect(instance)
        self.assertEqual(yields[-1][0], EMPTY_ANSWER_NOTICE)

    def test_repaired_answer_reaches_the_caller(self):
        # needs_grounding_repair must fire for this draft; the rewrite that
        # follows the stream has to be what the caller sees last.
        instance, _ = self._backend(["I cannot answer that."], repair="Actually, page 1 says X.")
        yields = self._collect(instance, repair_needed=True)
        self.assertEqual(yields[-1][0], "Actually, page 1 says X.")

    def test_an_empty_repair_does_not_destroy_the_draft(self):
        # A repair that returns nothing must leave the usable answer alone.
        instance, _ = self._backend(["Here is the answer."], repair="")
        yields = self._collect(instance, repair_needed=True)
        self.assertEqual(yields[-1][0], "Here is the answer.")

    def test_empty_answer_is_cached_as_the_notice(self):
        instance, _ = self._backend([""])
        self._collect(instance)
        cached = instance.cache.put.call_args[0][1]
        self.assertEqual(cached["answer"], EMPTY_ANSWER_NOTICE)


class NonStreamingEmptyAnswerTests(unittest.TestCase):
    def test_ask_reports_an_empty_completion_instead_of_returning_none(self):
        import asyncio

        from agentic_docuchat.rag import backend as backend_mod

        instance = object.__new__(backend_mod.RagBackend)
        instance.document_ready = True
        instance.document_version = "v1"
        instance.ollama_model = "m"
        instance._last_request_time = {}
        instance.rate_limit_seconds = 0
        instance.rate_limit_max_users = 1024
        instance.memory = mock.Mock()
        instance.memory.cache_key.return_value = "k"
        instance.memory.recent_turns_text.return_value = ""
        instance.memory.memories_text.return_value = ""
        instance.cache = mock.Mock()
        instance.cache.get.return_value = None
        instance._use_agent = lambda provider: False
        instance._retrieve = lambda q, k=None, fetch_k=None: ("CTX", ["d — p1"], [])

        model = mock.Mock()
        with mock.patch(
            "agentic_docuchat.rag.backend.init_chat_model", return_value=model
        ):
            model.ainvoke = mock.AsyncMock(
                return_value=mock.Mock(content="", additional_kwargs={})
            )
            instance._get_model = lambda provider: (model, "m")
            with mock.patch("agentic_docuchat.rag.backend.needs_grounding_repair", return_value=False):
                result = asyncio.run(instance._ask_impl("q", "u", "llamacpp"))
        self.assertEqual(result["answer"], EMPTY_ANSWER_NOTICE)
