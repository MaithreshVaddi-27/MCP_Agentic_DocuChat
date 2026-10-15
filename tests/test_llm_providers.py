import unittest

from agentic_docuchat.llm.ollama import detect_gpu


class ProviderProbeTests(unittest.TestCase):
    def test_gpu_detection_returns_a_consistent_shape(self):
        """Whatever this machine has (or has not), the status panel depends on
        these three keys always being present."""
        result = detect_gpu()
        self.assertIn("available", result)
        self.assertIn("kind", result)
        self.assertIn("details", result)
        self.assertIsInstance(result["available"], bool)


if __name__ == "__main__":
    unittest.main()
