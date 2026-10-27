"""Static contract checks; these never import the service or contact Docker."""

import ast
import hashlib
import hmac
import json
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MAIN = ROOT / "apps" / "runner" / "runner_service" / "main.py"


def _runner_method(name: str) -> ast.FunctionDef:
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    runner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Runner")
    return next(node for node in runner.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _container_create(method: ast.FunctionDef) -> ast.Call:
    for node in ast.walk(method):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "create" and isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "containers":
            return node
    raise AssertionError("container creation call not found")


def _static_value(node: ast.AST, values: dict[str, object] | None = None):
    values = values or {}
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
        left, right = _static_value(node.left, values), _static_value(node.right, values)
        return left + right if isinstance(node.op, ast.Add) else left - right if isinstance(node.op, ast.Sub) else left * right
    raise AssertionError(f"unsupported static expression: {ast.dump(node)}")


def _constants(tree: ast.Module) -> dict[str, object]:
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = _static_value(node.value, values)
            except (AssertionError, KeyError, TypeError):
                continue
    return values


class RunnerStaticContract(unittest.TestCase):
    def test_content_loader_rejects_changed_public_or_hidden_content_without_running_service(self):
        # Execute only the extracted JSON loader, never the service or Docker code.
        class ContentError(Exception):
            def __init__(self, status_code, detail):
                self.status_code = status_code
        import re
        scope = {"json": json, "re": re, "hashlib": hashlib, "hmac": hmac, "HTTPException": ContentError}
        module = ast.Module(body=[_runner_method("_load_tests")], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(MAIN), "exec"), scope)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("coding", "coding-private"):
                shutil.copytree(ROOT/"content"/name, root/name)
            owner = SimpleNamespace(content_root=root)
            path = root/"coding/backend_frequency_counts.json"
            problem = json.loads(path.read_text())
            hidden_path = root/"coding-private"/(problem["hidden_test_set"]+".json")
            hidden = json.loads(hidden_path.read_text())
            digest = hashlib.sha256(json.dumps({"problem": problem, "hidden": hidden}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            load = scope["_load_tests"]
            self.assertEqual(len(load(owner, problem["problem_id"], "run", digest)[1]), len(problem["public_tests"]))
            self.assertGreater(len(load(owner, problem["problem_id"], "submit", digest)[1]), len(problem["public_tests"]))
            for changed_path, changed in ((path, {**problem, "statement": "changed"}), (hidden_path, {**hidden, "tests": [{"stdin": "changed", "stdout": "changed"}]})):
                original = changed_path.read_text()
                changed_path.write_text(json.dumps(changed))
                for mode in ("run", "submit"):
                    with self.assertRaises(ContentError) as raised:
                        load(owner, problem["problem_id"], mode, digest)
                    self.assertEqual(raised.exception.status_code, 409)
                changed_path.write_text(original)

    def test_candidate_container_has_required_isolation_settings(self):
        call = _container_create(_runner_method("_container"))
        args = {kw.arg: kw.value for kw in call.keywords}
        module = ast.parse(MAIN.read_text(encoding="utf-8"))
        constants = _constants(module)
        self.assertEqual(ast.literal_eval(args["runtime"]), "runsc")
        self.assertIs(ast.literal_eval(args["network_disabled"]), True)
        self.assertIs(ast.literal_eval(args["read_only"]), True)
        self.assertEqual(ast.literal_eval(args["user"]), "65534:65534")
        self.assertEqual(ast.literal_eval(args["cap_drop"]), ["ALL"])
        self.assertEqual(ast.literal_eval(args["security_opt"]), ["no-new-privileges"])
        self.assertEqual(_static_value(args["pids_limit"], constants), 64)
        self.assertEqual(_static_value(args["nano_cpus"], constants), 1_000_000_000)
        self.assertEqual(ast.unparse(args["mem_limit"]), "memory")
        self.assertIn("TMPFS_BYTES", ast.unparse(args["tmpfs"]))
        self.assertNotIn("volumes", args)
        self.assertNotIn("mounts", args)

    def test_preflight_is_runsc_backed_bounded_and_fixed(self):
        method = _runner_method("initialize")
        create_calls = [node for node in ast.walk(method) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "create"]
        self.assertTrue(create_calls, "preflight container should be created explicitly")
        call = create_calls[0]
        values = {kw.arg: kw.value for kw in call.keywords}
        self.assertEqual(ast.literal_eval(values["runtime"]), "runsc")
        self.assertIs(ast.literal_eval(values["network_disabled"]), True)
        self.assertIs(ast.literal_eval(values["read_only"]), True)
        self.assertEqual(ast.literal_eval(values["entrypoint"]), "/bin/sh")
        wait_calls = [node for node in ast.walk(method) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "wait"]
        self.assertTrue(any(ast.literal_eval(next(kw.value for kw in c.keywords if kw.arg == "timeout")) == 10 for c in wait_calls))
        preflight = ast.unparse(method)
        self.assertIn("compile_images.values()", preflight)
        self.assertIn("runtime_images.values()", preflight)

    def test_process_limits_and_bounded_output_are_enforced_in_code(self):
        module = ast.parse(MAIN.read_text(encoding="utf-8"))
        constants = _constants(module)
        self.assertEqual(constants["SOURCE_LIMIT"], 64 * 1024)
        self.assertEqual(constants["OUTPUT_LIMIT"], 64 * 1024)
        self.assertEqual(constants["RUN_TIMEOUT"], 2.0)
        self.assertEqual(constants["COMPILE_TIMEOUT"], 15.0)
        self.assertEqual(constants["SUITE_TIMEOUT"], 30.0)
        self.assertEqual(constants["MEMORY_BYTES"], 256 * 1024 * 1024)
        self.assertEqual(constants["COMPILE_MEMORY_BYTES"], 1024 * 1024 * 1024)
        self.assertEqual(constants["TMPFS_BYTES"], 64 * 1024 * 1024)
        bounded = ast.unparse(_runner_method("_exec_bounded"))
        self.assertIn("OUTPUT_LIMIT", bounded)
        self.assertIn("container.kill()", bounded)
        self.assertGreaterEqual(bounded.count("exceeded.is_set()"), 2)
        self.assertIn("part[:max(0, room)]", bounded)

    def test_cpp_runtime_is_separate_and_has_no_compiler(self):
        runtime = (ROOT / "apps" / "runner" / "Dockerfile.cpp-runtime").read_text(encoding="utf-8").lower()
        compiler = (ROOT / "apps" / "runner" / "Dockerfile.cpp").read_text(encoding="utf-8").lower()
        python = (ROOT / "apps" / "runner" / "Dockerfile.python").read_text(encoding="utf-8").lower()
        self.assertIn("libstdc++6", runtime)
        for tool in ("g++", "gcc", "clang"):
            self.assertNotIn(tool, runtime)
        self.assertIn("gcc:12.2.0-bookworm", compiler)
        for dockerfile in (compiler, python, runtime):
            self.assertIn("user nobody:nogroup", dockerfile)
            self.assertNotIn("useradd", dockerfile)

    def test_timeout_or_output_breach_stops_suite_after_container_cleanup(self):
        method = _runner_method("_execute")
        loop = next(node for node in ast.walk(method) if isinstance(node, ast.For)
                    and isinstance(node.target, ast.Tuple))
        guard = next(node for node in loop.body if isinstance(node, ast.If)
                     and ast.unparse(node.test) == "results[-1]['kind'] in {'timeout', 'output_limit'}")
        self.assertTrue(any(isinstance(node, ast.Break) for node in guard.body))
        cleanup = next(node for node in loop.body if isinstance(node, ast.Try))
        self.assertIn("case.remove(force=True, v=True)", ast.unparse(ast.Module(body=cleanup.finalbody, type_ignores=[])))
        self.assertLess(loop.body.index(cleanup), loop.body.index(guard))
        self.assertIn("('timeout', 'output_limit', 'compile_error', 'runtime_error', 'wrong_answer')", ast.unparse(method))

    def test_cpp_compile_and_runtime_images_are_distinct(self):
        tree = ast.parse(MAIN.read_text(encoding="utf-8"))
        runner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Runner")
        initializer = next(node for node in runner.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
        init_text = ast.unparse(initializer)
        self.assertIn("RUNNER_CPP_COMPILE_IMAGE", init_text)
        self.assertIn("RUNNER_CPP_RUNTIME_IMAGE", init_text)
        self.assertIn("self.compile_images", init_text)
        self.assertIn("self.runtime_images", init_text)
        container_text = ast.unparse(_runner_method("_container"))
        self.assertIn("compile_phase", container_text)
        self.assertIn("self.compile_images", container_text)
        self.assertIn("self.runtime_images", container_text)

    def test_runner_database_never_serializes_source_text(self):
        method = ast.unparse(_runner_method("enqueue"))
        self.assertIn("source_sha256", method)
        self.assertNotIn("model_dump_json", method)
        self.assertNotIn("request.source", method.replace("request.source.encode", ""))

    def test_duplicate_job_lookup_precedes_busy_rejection(self):
        method = ast.unparse(_runner_method("enqueue"))
        self.assertLess(method.index("SELECT status FROM jobs"), method.index("worker_active.is_set()"))

    def test_public_scenarios_and_coding_records_do_not_embed_private_answers(self):
        for path in (ROOT / "content" / "scenarios").glob("*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("private_reference_id", record)
            self.assertNotIn("causal_reference", record)
            self.assertNotIn("criterion_anchors", record)
            for card in record["public_evidence"]:
                self.assertEqual(card.get("requires", []), [])
        for path in (ROOT / "content" / "coding").glob("*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("hidden_test_set", record)
            self.assertNotIn("hidden_tests", record)


if __name__ == "__main__":
    unittest.main()
