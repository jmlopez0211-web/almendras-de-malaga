"""Resume queue tests: a product is retried once per engine version by default."""
import ast
import unittest
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "catalog_candidate_batch.py"
TREE = ast.parse(SCRIPT.read_text(encoding="utf-8"))
NEEDED = {"ENGINE_VERSION", "select_resume_products", "recover_interrupted_product"}
selected = []
for node in TREE.body:
    if isinstance(node, ast.FunctionDef) and node.name in NEEDED:
        selected.append(node)
    elif isinstance(node, ast.Assign):
        names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if names & NEEDED:
            selected.append(node)

namespace = {"time": time}
exec(compile(ast.Module(body=selected, type_ignores=[]), str(SCRIPT), "exec"), namespace)
ENGINE_VERSION = namespace["ENGINE_VERSION"]
select_resume_products = namespace["select_resume_products"]
recover_interrupted_product = namespace["recover_interrupted_product"]


class TestResumeQueue(unittest.TestCase):
    PRODUCTS = [
        ("a", "Product A"),
        ("b", "Product B"),
        ("c", "Product C"),
        ("d", "Product D"),
    ]

    def test_old_no_result_is_retried_once(self):
        processed = {"a": {"status": "NO_RESULTS_RELEVANT"}}
        first = select_resume_products(
            self.PRODUCTS, processed, retry_no_candidates=True
        )
        self.assertEqual(first, self.PRODUCTS)
        processed["a"]["last_resume_engine_version"] = ENGINE_VERSION
        second = select_resume_products(
            self.PRODUCTS, processed, retry_no_candidates=True
        )
        self.assertEqual(second, self.PRODUCTS[1:])

    def test_old_source_error_moves_on_after_one_attempt(self):
        processed = {"a": {"status": "SOURCE_ERROR"}}
        first = select_resume_products(self.PRODUCTS, processed)
        self.assertEqual(first, self.PRODUCTS)
        processed["a"]["last_resume_engine_version"] = ENGINE_VERSION
        second = select_resume_products(self.PRODUCTS, processed)
        self.assertEqual(second, self.PRODUCTS[1:])

    def test_force_retry_overrides_version_guard(self):
        processed = {
            "a": {
                "status": "CANDIDATES_FOUND_DOWNLOAD_FAILED",
                "last_resume_engine_version": ENGINE_VERSION,
            }
        }
        result = select_resume_products(
            self.PRODUCTS, processed, force_retry=True
        )
        self.assertEqual(result, self.PRODUCTS)

    def test_downloaded_candidate_only_rechecks_when_requested(self):
        processed = {"a": {"status": "DOWNLOADED_UNVERIFIED"}}
        normal = select_resume_products(self.PRODUCTS, processed)
        self.assertEqual(normal, self.PRODUCTS[1:])
        recheck = select_resume_products(
            self.PRODUCTS, processed, recheck_downloaded=True
        )
        self.assertEqual(recheck, self.PRODUCTS)

    def test_no_results_are_not_retried_without_explicit_flag(self):
        processed = {"a": {"status": "NO_RESULTS_RELEVANT"}}
        result = select_resume_products(self.PRODUCTS, processed)
        self.assertEqual(result, self.PRODUCTS[1:])


    def test_interrupted_product_is_not_retried_in_a_restart_loop(self):
        processed = {
            "a": {
                "status": "INTERRUPTED",
                "last_resume_engine_version": ENGINE_VERSION,
            }
        }
        normal = select_resume_products(self.PRODUCTS, processed)
        self.assertEqual(normal, self.PRODUCTS[1:])
        forced = select_resume_products(self.PRODUCTS, processed, force_retry=True)
        self.assertEqual(forced, self.PRODUCTS)


    def test_interrupted_checkpoint_is_recovered_once(self):
        state = {"in_progress": {
            "product_key": "a", "product": "Product A", "engine_version": ENGINE_VERSION
        }}
        processed = {}
        key = recover_interrupted_product(state, processed)
        self.assertEqual(key, "a")
        self.assertNotIn("in_progress", state)
        self.assertEqual(processed["a"]["status"], "INTERRUPTED")
        self.assertEqual(processed["a"]["last_resume_engine_version"], ENGINE_VERSION)
        self.assertIsNone(recover_interrupted_product(state, processed))


if __name__ == "__main__":
    unittest.main()
