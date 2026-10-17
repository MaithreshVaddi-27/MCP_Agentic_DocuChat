"""On-disk model discovery — the thing that makes an offline machine useful.

Every test builds a throwaway Ollama/Hugging Face layout in a temp dir and
points OLLAMA_HOME / HF_HOME / LLAMACPP_MODEL_DIRS at it, so nothing depends
on what happens to be installed on the machine running the suite.
"""

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from agentic_docuchat.llm import discovery

# Verbatim output from the real runtimes on this machine, so the parsers are
# tested against what they will actually meet rather than a tidy paraphrase.
OLLAMA_LIST = """NAME          ID              SIZE      MODIFIED
qwen3:1.7b    8f68893c685c    1.4 GB    3 weeks ago
gemma3:1b     8648f39daa8f    815 MB    5 weeks ago
"""

LLAMACPP_CACHE_LIST = """number of models in cache: 3
   1. ggml-org/SmolLM3-3B-GGUF:Q4_K_M
   2. second-state/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M
   3. LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M
"""

# The first row is the widest repo id in the table, so it is followed by a
# SINGLE space before REPO TYPE. Column-padding parsers get this wrong.
MLX_SCAN = """Scanning Hugging Face cache for models with pattern "mlx".
REPO ID                                       REPO TYPE SIZE ON DISK NB FILES LAST_ACCESSED LAST_MODIFIED LOCAL PATH
--------------------------------------------- --------- ------------ -------- ------------- ------------ ----------------------------------------------------------------------------------------------
mlx-community/LFM2.5-1.2B-Instruct-OptiQ-4bit model           864.7M        9 2 weeks ago   2 weeks ago   /Users/me/.cache/huggingface/hub/models--mlx-community--LFM2.5-1.2B-Instruct-OptiQ-4bit
mlx-community/Qwen3.5-2B-MLX-4bit             model           1.7G       10 2 weeks ago   2 weeks ago   /Users/me/.cache/huggingface/hub/models--mlx-community--Qwen3.5-2B-MLX-4bit
"""


@contextmanager
def hermetic(**cli):
    """Throwaway cache layout plus a fully stubbed runtime CLI.

    Both halves are needed: discovery asks the installed runtimes first, and
    falls back to the cache directories second, so a developer's real
    `ollama list` or real Hugging Face cache would otherwise answer the test
    instead of the fixture. `cli` maps a binary name to its verbatim output;
    anything not named behaves as "not installed".

    Yields the temp root, so tests can plant files to exercise the fallback.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "ollama").mkdir()
        (root / "hub").mkdir()
        (root / "models").mkdir()
        env = {
            "OLLAMA_HOME": str(root / "ollama"),
            "HF_HOME": str(root),
            "LLAMACPP_MODEL_DIRS": str(root / "models"),
        }
        runner = mock.patch.object(
            discovery, "_run", side_effect=lambda argv: cli.get(argv[0], "")
        )
        with mock.patch.dict(os.environ, env, clear=False), runner:
            yield root


def fake_home():
    """No runtimes installed — exercise only the on-disk fallbacks."""
    return hermetic()


def _write_ollama_manifest(root: Path, *relative: str) -> None:
    for parts in relative:
        path = root / "ollama" / "models" / "manifests" / parts
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")


def _write_hub_repo(root: Path, repo: str, files: dict[str, bytes]) -> None:
    for name, payload in files.items():
        path = root / "hub" / repo / "snapshots" / "abc123" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


class OllamaDiscoveryTests(unittest.TestCase):
    def test_manifest_path_is_the_tag(self):
        with fake_home() as root:
            _write_ollama_manifest(
                root,
                "registry.ollama.ai/library/gemma3/1b",
                "registry.ollama.ai/library/gemma3/4b",
                "registry.ollama.ai/library/qwen3/1.7b",
            )
            self.assertEqual(
                discovery.ollama_models_on_disk(),
                ["gemma3:1b", "gemma3:4b", "qwen3:1.7b"],
            )

    def test_non_library_namespace_is_kept(self):
        with fake_home() as root:
            _write_ollama_manifest(root, "registry.ollama.ai/acme/private-model/1.0")
            self.assertEqual(discovery.ollama_models_on_disk(), ["acme/private-model:1.0"])

    def test_dotfiles_are_not_models(self):
        """macOS litters the manifests tree with .DS_Store; one of those once
        showed up in the picker as a model called 'library:.DS_Store'."""
        with fake_home() as root:
            _write_ollama_manifest(
                root,
                "registry.ollama.ai/library/.DS_Store",
                "registry.ollama.ai/library/gemma3/1b",
            )
            self.assertEqual(discovery.ollama_models_on_disk(), ["gemma3:1b"])

    def test_missing_home_is_empty_not_an_error(self):
        with fake_home() as root:
            os.environ["OLLAMA_HOME"] = str(root / "nope")
            self.assertEqual(discovery.ollama_models_on_disk(), [])


class LlamaCppDiscoveryTests(unittest.TestCase):
    def test_hub_repo_is_reported_as_org_repo(self):
        with fake_home() as root:
            _write_hub_repo(
                root,
                "models--ggml-org--SmolLM3-3B-GGUF",
                {"model.Q4_K_M.gguf": b"x" * 32},
            )
            self.assertEqual(discovery.gguf_models_on_disk(), ["ggml-org/SmolLM3-3B-GGUF"])

    def test_sharded_files_collapse_to_one_model(self):
        with fake_home() as root:
            _write_hub_repo(
                root,
                "models--org--Big-Model-GGUF",
                {
                    "model-00001-of-00003.gguf": b"x",
                    "model-00002-of-00003.gguf": b"x",
                    "model-00003-of-00003.gguf": b"x",
                },
            )
            self.assertEqual(len(discovery.gguf_models_on_disk()), 1)

    def test_interrupted_download_is_not_offered(self):
        """A repo holding only a .downloadInProgress blob would 404 the moment
        llama-server tried to load it — it must not be advertised."""
        with fake_home() as root:
            blob = root / "hub" / "models--org--Half-Pulled-GGUF" / "blobs"
            blob.mkdir(parents=True)
            (blob / "abc.downloadInProgress").write_bytes(b"partial")
            self.assertEqual(discovery.gguf_models_on_disk(), [])

    def test_plain_model_directory_is_reported_by_path(self):
        with fake_home() as root:
            model_dir = root / "models"
            (model_dir / "tiny.gguf").write_bytes(b"x")
            self.assertEqual(discovery.gguf_models_on_disk(), [str(model_dir / "tiny.gguf")])


class MlxDiscoveryTests(unittest.TestCase):
    def test_mlx_repo_with_weights_is_reported(self):
        with fake_home() as root:
            _write_hub_repo(
                root,
                "models--mlx-community--Qwen3.5-2B-MLX-4bit",
                {"model.safetensors": b"weights" * 16},
            )
            self.assertEqual(
                discovery.mlx_models_on_disk(),
                ["mlx-community/Qwen3.5-2B-MLX-4bit"],
            )

    def test_config_only_repo_is_not_offered(self):
        """mlx-lm leaves a snapshot with just a config when it merely inspects
        a repo; naming that as a model would send the user to a server that
        dies on load."""
        with fake_home() as root:
            _write_hub_repo(
                root,
                "models--mlx-community--gemma-3-4b-it-4bit",
                {"config.json": b"{}", "tokenizer.json": b"{}"},
            )
            self.assertEqual(discovery.mlx_models_on_disk(), [])

    def test_non_mlx_repos_are_ignored(self):
        with fake_home() as root:
            _write_hub_repo(
                root,
                "models--BAAI--bge-base-en-v1.5",
                {"model.safetensors": b"embedding-weights" * 8},
            )
            self.assertEqual(discovery.mlx_models_on_disk(), [])


class OllamaListTests(unittest.TestCase):
    """`ollama list` is authoritative when the daemon answers."""

    def test_tags_come_from_the_name_column(self):
        with hermetic(ollama=OLLAMA_LIST):
            self.assertEqual(discovery.ollama_models_on_disk(), ["gemma3:1b", "qwen3:1.7b"])

    def test_missing_binary_or_daemon_is_not_an_error(self):
        with hermetic(ollama=""):
            self.assertEqual(discovery.ollama_models_on_disk(), [])

    def test_falls_back_to_disk_when_the_daemon_is_down(self):
        with hermetic(ollama="") as root:
            _write_ollama_manifest(root, "registry.ollama.ai/library/gemma3/1b")
            self.assertEqual(discovery.ollama_models_on_disk(), ["gemma3:1b"])


class LlamaCppCacheListTests(unittest.TestCase):
    """`llama-server --cache-list` works with no server running."""

    def test_numbered_rows_yield_repo_and_quant(self):
        with hermetic(**{"llama-server": LLAMACPP_CACHE_LIST}):
            models = discovery.gguf_models_on_disk()
        self.assertEqual(
            models,
            [
                "LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M",
                "ggml-org/SmolLM3-3B-GGUF:Q4_K_M",
                "second-state/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M",
            ],
        )

    def test_quant_entry_wins_over_the_bare_hub_id(self):
        # Same model from both sources must appear once, keeping the quant tag
        # llama-server actually cached.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "hub" / "models--ggml-org--SmolLM3-3B-GGUF" / "snapshots" / "abc"
            snapshot.mkdir(parents=True)
            (snapshot / "w.gguf").write_bytes(b"G")
            env = {"HF_HOME": str(root), "LLAMACPP_MODEL_DIRS": str(root / "none")}
            with mock.patch.dict(os.environ, env):
                with hermetic(**{"llama-server": LLAMACPP_CACHE_LIST}):
                    models = discovery.gguf_models_on_disk()
        self.assertEqual(models.count("ggml-org/SmolLM3-3B-GGUF:Q4_K_M"), 1)
        self.assertNotIn("ggml-org/SmolLM3-3B-GGUF", models)

    def test_summary_line_is_not_parsed_as_a_model(self):
        with hermetic(**{"llama-server": LLAMACPP_CACHE_LIST}):
            for model in discovery.gguf_models_on_disk():
                self.assertNotIn("number", model)

    def test_missing_binary_is_not_an_error(self):
        with hermetic(**{"llama-server": ""}):
            self.assertEqual(discovery.gguf_models_on_disk(), [])


class MlxScanTests(unittest.TestCase):
    """`mlx_lm.manage --scan` output is column-aligned, not space-aligned."""

    def test_repo_id_column_is_extracted(self):
        with hermetic(**{"mlx_lm.manage": MLX_SCAN}):
            self.assertEqual(
                discovery.mlx_models_on_disk(),
                [
                    "mlx-community/LFM2.5-1.2B-Instruct-OptiQ-4bit",
                    "mlx-community/Qwen3.5-2B-MLX-4bit",
                ],
            )

    def test_widest_repo_id_does_not_swallow_the_type_column(self):
        # The first row has a single space before "model"; a 2+ space split
        # would return "...-4bit model", which no runtime can load.
        with hermetic(**{"mlx_lm.manage": MLX_SCAN}):
            for repo in discovery.mlx_models_on_disk():
                self.assertNotIn(" ", repo)
                self.assertTrue(repo.endswith("4bit"))

    def test_header_and_rule_rows_are_ignored(self):
        with hermetic(**{"mlx_lm.manage": MLX_SCAN}):
            models = discovery.mlx_models_on_disk()
        self.assertNotIn("REPO", " ".join(models))
        self.assertNotIn("---", " ".join(models))

    def test_missing_binary_is_not_an_error(self):
        with hermetic(**{"mlx_lm.manage": ""}):
            self.assertEqual(discovery.mlx_models_on_disk(), [])


class StartHintTests(unittest.TestCase):
    """The hint gets copy-pasted, so it has to be a command that actually runs.

    `llama-server -hf` takes `<user>/<model>[:quant]`; a hand-placed
    `~/llama.cpp/models/foo.gguf` has to be passed positionally instead.
    """

    def test_local_gguf_is_passed_positionally_not_via_hf(self):
        with fake_home() as root:
            (root / "models" / "my-model.gguf").write_bytes(b"GGUF")
            hint = discovery.start_hint("llamacpp")
        self.assertNotIn("-hf", hint)
        self.assertIn("my-model.gguf", hint)

    def test_local_path_is_quoted_because_it_may_contain_spaces(self):
        with fake_home() as root:
            (root / "models" / "my model.gguf").write_bytes(b"GGUF")
            hint = discovery.start_hint("llamacpp")
        self.assertIn(f'"{root}/models/my model.gguf"', hint)

    def test_cached_repo_uses_the_hf_flag_with_its_quant(self):
        with hermetic(**{"llama-server": LLAMACPP_CACHE_LIST}):
            hint = discovery.start_hint("llamacpp")
        cached = {
            "ggml-org/SmolLM3-3B-GGUF:Q4_K_M",
            "second-state/SmolLM2-1.7B-Instruct-GGUF:Q4_K_M",
            "LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M",
        }
        self.assertIn(hint.split()[2].removeprefix("-hf"), cached)

    def test_repo_is_preferred_over_a_local_file(self):
        # A local file can sort first; the hint must still be runnable.
        with fake_home() as root:
            (root / "models" / "aaa-local.gguf").write_bytes(b"GGUF")
            snapshot = root / "hub" / "models--ggml-org--SmolLM3-3B-GGUF" / "snapshots" / "a"
            snapshot.mkdir(parents=True)
            (snapshot / "w.gguf").write_bytes(b"G")
            hint = discovery.start_hint("llamacpp")
        self.assertIn("-hf ggml-org/SmolLM3-3B-GGUF", hint)
        self.assertNotIn("aaa-local", hint)

    def test_empty_disk_gives_a_download_command(self):
        with fake_home():
            self.assertIn("-hf Qwen/Qwen3-4B-GGUF:Q4_0", discovery.start_hint("llamacpp"))

    def test_ollama_hint_skips_pull_when_models_exist(self):
        with hermetic(ollama=OLLAMA_LIST):
            self.assertEqual(discovery.start_hint("ollama"), "ollama serve")

    def test_ollama_hint_tells_you_to_pull_when_nothing_is_cached(self):
        with hermetic(ollama=""):
            self.assertEqual(
                discovery.start_hint("ollama"), "ollama serve && ollama pull gemma3:4b"
            )

    def test_mlx_hint_uses_a_real_repo_when_cached(self):
        with hermetic(**{"mlx_lm.manage": MLX_SCAN}):
            hint = discovery.start_hint("mlx")
        self.assertIn(
            "mlx_lm.server --model mlx-community/LFM2.5-1.2B-Instruct-OptiQ-4bit", hint
        )

    def test_mlx_hint_falls_back_to_a_default_repo(self):
        with fake_home():
            self.assertIn(
                "mlx_lm.server --model mlx-community/gemma-3-4b-it-4bit",
                discovery.start_hint("mlx"),
            )

    def test_unknown_provider_has_no_hint(self):
        self.assertEqual(discovery.start_hint("nope"), "")


class SubprocessTests(unittest.TestCase):
    """_run must never raise — it sits on the UI status path."""

    def test_missing_binary_returns_empty(self):
        with mock.patch.object(discovery, "_which", return_value=None):
            self.assertEqual(discovery._run(("definitely-not-installed",)), "")

    def test_nonzero_exit_returns_empty(self):
        with mock.patch.object(discovery, "_which", return_value="/bin/false"):
            self.assertEqual(discovery._run(("false",)), "")

    def test_timeout_returns_empty(self):
        import subprocess as sp

        with mock.patch.object(discovery, "_which", return_value="/bin/sleep"):
            with mock.patch.object(discovery.subprocess, "run", side_effect=sp.TimeoutExpired("sleep", 1)):
                self.assertEqual(discovery._run(("sleep", "10")), "")

    def test_which_finds_a_binary_outside_path(self):
        # GUI launches can lack a login-shell PATH; homebrew/pipx dirs are tried.
        # The candidate is stat'ed for real, so this has to point at a file we
        # create — a hardcoded /opt/homebrew path passes only on a Mac that
        # happens to have llama.cpp installed, and silently fails on CI.
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "llama-server"
            binary.write_text("#!/bin/sh\n")
            binary.chmod(0o755)
            with mock.patch.object(discovery.shutil, "which", return_value=None):
                with mock.patch.object(discovery, "_EXTRA_BIN_DIRS", (Path(tmp),)):
                    found = discovery._which("llama-server")
            self.assertEqual(found, str(binary))

    def test_which_skips_a_non_executable_file(self):
        # Present but not runnable is not a usable binary — must not be returned.
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "llama-server"
            binary.write_text("#!/bin/sh\n")
            binary.chmod(0o644)
            with mock.patch.object(discovery.shutil, "which", return_value=None):
                with mock.patch.object(discovery, "_EXTRA_BIN_DIRS", (Path(tmp),)):
                    self.assertIsNone(discovery._which("llama-server"))


if __name__ == "__main__":
    unittest.main()
