"""Behavioral tests for the compact Cargo diagnostics runner."""
import importlib.util
from contextlib import contextmanager
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "rust_diagnostics.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("rust_diagnostics", RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FAKE_CARGO = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys
import time

Path(os.environ["CARGO_CAPTURE_PATH"]).write_text(
    json.dumps(sys.argv[1:]), encoding="utf-8")
mode = os.environ.get("FAKE_CARGO_MODE", "success")
if mode == "stream":
    message = {
        "reason": "compiler-message",
        "package_id": "demo 0.1.0 (path+file:///demo)",
        "target": {"name": "demo", "kind": ["lib"]},
        "message": {
            "level": "error", "message": "mismatched types", "code": {"code": "E0308"},
            "spans": [], "children": [], "rendered": "private rendered output",
        },
    }
    encoded = (json.dumps(message) + "\n").encode()
    split = len(encoded) // 2
    os.write(sys.stdout.fileno(), encoded[:split])
    sys.stdout.flush()
    time.sleep(0.02)
    os.write(sys.stdout.fileno(), encoded[split:])
    os.write(sys.stdout.fileno(), b"build-script marker\n")
    os.write(sys.stderr.fileno(), b"linker detail\n")
    raise SystemExit(101)
if mode == "timeout":
    child = subprocess.Popen([
        sys.executable, "-c", "import time; time.sleep(60)"
    ])
    Path(os.environ["CARGO_PIDS_PATH"]).write_text(
        json.dumps([os.getpid(), child.pid]), encoding="utf-8")
    os.write(sys.stdout.fileno(), b"partial stdout\n")
    os.write(sys.stderr.fileno(), b"partial stderr\n")
    time.sleep(60)
if mode == "closed-stdout":
    os.close(sys.stdout.fileno())
    time.sleep(2)
raise SystemExit(int(os.environ.get("FAKE_CARGO_EXIT", "0")))
'''


class RunnerFixture(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RUNNER.exists(), "The Rust diagnostics runner is not implemented")
        self.rd = load_runner()
        self.temp = tempfile.TemporaryDirectory(prefix="test-rust-diagnostics-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.capture = self.root / "cargo-args.json"
        self.pids = self.root / "cargo-pids.json"
        cargo = self.bin_dir / "cargo"
        cargo.write_text(FAKE_CARGO, encoding="utf-8")
        cargo.chmod(0o755)
        env = dict(os.environ)
        env.update({
            "PATH": str(self.bin_dir) + os.pathsep + env.get("PATH", ""),
            "CARGO_CAPTURE_PATH": str(self.capture),
            "CARGO_PIDS_PATH": str(self.pids),
        })
        self.environment = patch.dict(os.environ, env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def assert_error(self, code, action):
        with self.assertRaises(self.rd.DiagnosticError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def main_output(self, argv):
        output = io.StringIO()
        with patch.object(self.rd.Path, "cwd", return_value=self.root), \
                redirect_stdout(output):
            code = self.rd.main(argv)
        raw = output.getvalue()
        self.assertEqual(len(raw.splitlines()), 1)
        self.assertLessEqual(len(raw.encode("utf-8")), 4096)
        return code, json.loads(raw), raw

    def make_run(self, messages=(), exit_code=0, timed_out=False,
                 interrupted_signal=None, non_json=()):
        artifact_root = self.root / ("artifacts-" + str(time.monotonic_ns()))
        artifact_root.mkdir(mode=0o700)
        artifacts = self.rd.RunArtifacts(
            root=artifact_root,
            stdout_path=artifact_root / "stdout.log",
            stderr_path=artifact_root / "stderr.log",
            diagnostics_path=artifact_root / "diagnostics.json",
            report_path=artifact_root / "report.json",
        )
        artifacts.stdout_path.write_bytes(b"")
        artifacts.stderr_path.write_bytes(b"")
        return self.rd.CargoRun(
            command=("cargo", "check", "--message-format=json", "--color=never"),
            cwd=self.root,
            exit_code=exit_code,
            timed_out=timed_out,
            interrupted_signal=interrupted_signal,
            started_at=10.0,
            ended_at=11.0,
            stdout_non_json=tuple(non_json),
            raw_messages=tuple(messages),
            artifacts=artifacts,
        )


def compiler_message(package, target, level="error", message="mismatched types",
                     code="E0308", spans=None, children=None):
    return {
        "reason": "compiler-message",
        "package_id": package,
        "target": {"name": target, "kind": ["lib"], "crate_types": ["lib"]},
        "message": {
            "level": level,
            "message": message,
            "code": {"code": code, "explanation": None} if code else None,
            "spans": [] if spans is None else spans,
            "children": [] if children is None else children,
            "rendered": "private rendered diagnostic",
        },
    }


def span(primary=True, replacement="value", applicability="MachineApplicable",
         expansion=None):
    return {
        "file_name": "src/lib.rs",
        "byte_start": 4,
        "byte_end": 7,
        "line_start": 2,
        "line_end": 2,
        "column_start": 5,
        "column_end": 8,
        "is_primary": primary,
        "text": [{"text": "let bad = old;", "highlight_start": 11,
                  "highlight_end": 14}],
        "label": "expected u32",
        "suggested_replacement": replacement,
        "suggestion_applicability": applicability,
        "expansion": expansion,
    }


def analysis_envelope(items=None):
    if items is None:
        items = [{
            "evidence_ids": ["D001"],
            "cause": "借用が同時に保持されています。",
            "fix": "可変借用のスコープを短くします。",
        }]
    return {
        "done": True,
        "done_reason": "stop",
        "response": json.dumps({"items": items}, ensure_ascii=False),
    }


@contextmanager
def ollama_stub(rd, response=None, status=200, delay=0, drip=False):
    requests = []

    class FakeSocket:
        def __init__(self):
            self.closed = threading.Event()

        def shutdown(self, _how):
            self.closed.set()

    class FakeResponse:
        def __init__(self, response_status, data):
            self.status = response_status
            self.data = data

        def read(self, _limit):
            return self.data

    class FakeConnection:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout
            self.sock = None

        def connect(self):
            self.sock = FakeSocket()

        def request(self, method, path, body, headers):
            requests.append((path, json.loads(body), self.host, self.port,
                             method, dict(headers)))

        def getresponse(self):
            if status == 0:
                raise ConnectionResetError("disconnected")
            if delay or drip:
                waited = self.sock.closed.wait(delay if delay else 1.0)
                if waited:
                    raise OSError("closed by deadline")
            data = response if isinstance(response, bytes) else json.dumps(
                analysis_envelope() if response is None else response).encode()
            return FakeResponse(status, data)

        def close(self):
            if self.sock is not None:
                self.sock.closed.set()

    with patch.object(rd.http.client, "HTTPConnection", FakeConnection):
        yield requests


class ArgumentTests(RunnerFixture):
    def test_preserves_toolchain_cargo_and_clippy_arguments(self):
        invocation = self.rd.parse_argv([
            "--toolchain", "stable", "clippy", "--",
            "-p", "core", "--features", "serde",
            "--manifest-path", "app/Cargo.toml", "--locked",
            "--", "-D", "warnings",
        ])
        self.assertEqual(invocation.tool, "clippy")
        self.assertEqual(invocation.toolchain, "stable")
        self.assertEqual(invocation.cargo_args[-3:], ("--", "-D", "warnings"))
        self.assertEqual(
            self.rd.build_cargo_command(invocation),
            ("cargo", "+stable", "clippy", "-p", "core", "--features", "serde",
             "--manifest-path", "app/Cargo.toml", "--locked",
             "--message-format=json", "--color=never", "--", "-D", "warnings"),
        )

    def test_check_arguments_are_literal_array_elements(self):
        dangerous = "name with spaces; $" + "(touch must-not-run)"
        invocation = self.rd.parse_argv(["check", "--", "-p", dangerous])
        self.assertEqual(
            self.rd.build_cargo_command(invocation),
            ("cargo", "check", "-p", dangerous,
             "--message-format=json", "--color=never"),
        )

    def test_invalid_wrapper_arguments_are_rejected(self):
        cases = (
            [], ["check"], ["build", "--"], ["--toolchain", "check", "--"],
            ["--toolchain", "", "check", "--"], ["check", "-p", "demo"],
        )
        for argv in cases:
            with self.subTest(argv=argv):
                self.assert_error("INVALID_ARGUMENTS", lambda argv=argv: self.rd.parse_argv(argv))

    def test_owned_output_and_fix_flags_are_rejected(self):
        cases = (
            ["check", "--", "--message-format", "json"],
            ["check", "--", "--message-format=json-diagnostic-rendered-ansi"],
            ["check", "--", "--color", "always"],
            ["clippy", "--", "--color=always"],
            ["check", "--", "--fix"],
            ["check", "--", "--fix=true"],
            ["clippy", "--", "--fix", "false"],
        )
        for argv in cases:
            with self.subTest(argv=argv):
                self.assert_error("INVALID_ARGUMENTS", lambda argv=argv: self.rd.parse_argv(argv))


class CargoProcessTests(RunnerFixture):
    def test_streams_split_json_and_preserves_non_json_evidence(self):
        with patch.dict(os.environ, {"FAKE_CARGO_MODE": "stream"}):
            run = self.rd.run_cargo(
                self.rd.parse_argv(["check", "--", "-p", "demo"]), self.root)
        self.assertEqual(run.exit_code, 101)
        self.assertFalse(run.timed_out)
        self.assertEqual(len(run.raw_messages), 1)
        self.assertEqual(run.raw_messages[0]["reason"], "compiler-message")
        self.assertEqual(run.stdout_non_json, ("build-script marker",))
        self.assertEqual(run.artifacts.root.stat().st_mode & 0o777, 0o700)
        self.assertTrue(run.artifacts.root.is_absolute())
        self.assertIn(b"private rendered output", run.artifacts.stdout_path.read_bytes())
        self.assertEqual(run.artifacts.stderr_path.read_bytes(), b"linker detail\n")
        self.assertEqual(json.loads(self.capture.read_text()), [
            "check", "-p", "demo", "--message-format=json", "--color=never"])

    def test_timeout_stops_the_owned_process_group_and_retains_partial_logs(self):
        with patch.dict(os.environ, {"FAKE_CARGO_MODE": "timeout"}), \
                patch.object(self.rd, "CARGO_TIMEOUT", 1.0), \
                patch.object(self.rd, "TERMINATE_GRACE", 0.1):
            run = self.rd.run_cargo(
                self.rd.parse_argv(["check", "--"]), self.root)
        self.assertTrue(run.timed_out)
        self.assertEqual(run.exit_code, 124)
        self.assertEqual(run.artifacts.stdout_path.read_bytes(), b"partial stdout\n")
        self.assertEqual(run.artifacts.stderr_path.read_bytes(), b"partial stderr\n")
        pids = json.loads(self.pids.read_text())
        for _ in range(100):
            if all(not self._alive(pid) for pid in pids):
                break
            time.sleep(0.01)
        self.assertTrue(all(not self._alive(pid) for pid in pids), pids)

    def test_deadline_still_applies_after_cargo_closes_stdout(self):
        with patch.dict(os.environ, {"FAKE_CARGO_MODE": "closed-stdout"}), \
                patch.object(self.rd, "CARGO_TIMEOUT", 0.5), \
                patch.object(self.rd, "TERMINATE_GRACE", 0.1):
            started = time.monotonic()
            run = self.rd.run_cargo(
                self.rd.parse_argv(["check", "--"]), self.root)
            elapsed = time.monotonic() - started
        self.assertEqual(run.exit_code, 124)
        self.assertTrue(run.timed_out)
        self.assertLess(elapsed, 1.0)

    @staticmethod
    def _alive(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True


class NormalizationTests(RunnerFixture):
    def test_deduplicates_only_exact_package_target_diagnostics(self):
        macro = {"span": span(primary=False, replacement=None),
                 "macro_decl_name": "demo!", "def_site_span": None}
        primary = span(expansion=macro)
        secondary = span(primary=False, replacement=None)
        children = [{
            "level": "help", "message": "consider using a value",
            "code": None, "spans": [span(replacement="42")], "rendered": None,
        }]
        first = compiler_message("pkg-a", "core", spans=[primary, secondary],
                                 children=children)
        same_other_package = compiler_message(
            "pkg-b", "core", spans=[primary, secondary], children=children)
        run = self.make_run([first, first, same_other_package], exit_code=101)

        items = self.rd.normalize_diagnostics(run)

        self.assertEqual((items.raw_error_count, items.unique_error_count), (3, 2))
        self.assertEqual((items.raw_warning_count, items.unique_warning_count), (0, 0))
        self.assertEqual([item.id for item in items.diagnostics], ["D001", "D002"])
        self.assertEqual(items.diagnostics[0].occurrences, 2)
        self.assertEqual(items.diagnostics[0].package_id, "pkg-a")
        self.assertEqual(items.diagnostics[0].target, "core:lib:lib")
        self.assertEqual(items.diagnostics[0].replacements[0].applicability,
                         "MachineApplicable")
        self.assertEqual(len(items.diagnostics[0].primary_spans), 1)
        self.assertEqual(len(items.diagnostics[0].secondary_spans), 1)

        self.rd.write_diagnostics_artifact(run, items)
        stored = json.loads(run.artifacts.diagnostics_path.read_text())
        self.assertEqual(stored["diagnostics"][0]["full_message"]["spans"][0]
                         ["expansion"]["macro_decl_name"], "demo!")
        self.assertEqual(stored["diagnostics"][0]["children"][0]["level"], "help")

    def test_counts_error_and_warning_levels_independently(self):
        run = self.make_run([
            compiler_message("pkg", "lib", level="warning", message="unused value",
                             code="unused_variables"),
            compiler_message("pkg", "lib", level="error"),
        ], exit_code=101)
        items = self.rd.normalize_diagnostics(run)
        self.assertEqual((items.raw_error_count, items.raw_warning_count), (1, 1))
        self.assertEqual((items.unique_error_count, items.unique_warning_count), (1, 1))

    def test_malformed_span_numbers_do_not_abort_diagnostic_capture(self):
        malformed = span()
        malformed["byte_start"] = "not-a-number"
        malformed["byte_end"] = None
        malformed["line_start"] = "bad"
        run = self.make_run([
            compiler_message("pkg", "lib", spans=[malformed]),
        ], exit_code=101)
        items = self.rd.normalize_diagnostics(run)
        self.assertEqual(items.unique_error_count, 1)
        self.assertEqual(items.diagnostics[0].replacements[0].byte_start, 0)
        packet = self.rd.build_analysis_packet(run, items)
        self.assertIsNotNone(packet)


class RoutingTests(RunnerFixture):
    def test_machine_applicable_requires_replacements_on_every_diagnostic(self):
        all_machine = self.rd.normalize_diagnostics(self.make_run([
            compiler_message("pkg", "lib", spans=[span()]),
            compiler_message("pkg", "lib", level="warning", message="style",
                             code="clippy::style", spans=[span(replacement="better")]),
        ], exit_code=101))
        mixed = self.rd.normalize_diagnostics(self.make_run([
            compiler_message("pkg", "lib", spans=[span()]),
            compiler_message("pkg", "lib", level="warning", message="style",
                             code="clippy::style",
                             spans=[span(replacement="maybe",
                                         applicability="MaybeIncorrect")]),
        ], exit_code=101))
        missing = self.rd.normalize_diagnostics(self.make_run([
            compiler_message("pkg", "lib", spans=[]),
        ], exit_code=101))
        self.assertTrue(self.rd.all_machine_applicable(all_machine))
        self.assertFalse(self.rd.all_machine_applicable(mixed))
        self.assertFalse(self.rd.all_machine_applicable(missing))

    def test_status_uses_cargo_outcome_and_warning_presence(self):
        clean_run = self.make_run([], exit_code=0)
        clean = self.rd.normalize_diagnostics(clean_run)
        warning_run = self.make_run([
            compiler_message("pkg", "lib", level="warning", message="style",
                             code="clippy::style")], exit_code=0)
        warnings = self.rd.normalize_diagnostics(warning_run)
        failed_run = self.make_run([], exit_code=101, non_json=("linker failed",))
        failed = self.rd.normalize_diagnostics(failed_run)
        timeout_run = self.make_run([], exit_code=124, timed_out=True)
        timeout = self.rd.normalize_diagnostics(timeout_run)
        self.assertEqual(self.rd.execution_status(clean_run, clean), "passed")
        self.assertEqual(self.rd.execution_status(warning_run, warnings), "warnings")
        self.assertEqual(self.rd.execution_status(failed_run, failed), "failed")
        self.assertEqual(self.rd.execution_status(timeout_run, timeout), "execution_error")


class PacketTests(RunnerFixture):
    def test_prioritizes_errors_and_records_diagnostic_coverage(self):
        messages = []
        for index in range(1, 26):
            level = "error" if index % 2 == 0 else "warning"
            messages.append(compiler_message(
                "pkg", "lib", level=level, message="diagnostic {:02d}".format(index),
                code="E{:04d}".format(index), spans=[span(replacement=None)]))
        run = self.make_run(messages, exit_code=101)
        items = self.rd.normalize_diagnostics(run)

        packet = self.rd.build_analysis_packet(run, items)

        self.assertIsNotNone(packet)
        self.assertLessEqual(len(packet.prompt.encode("utf-8")), 24 * 1024)
        self.assertEqual(packet.selected_ids[:2], ("D002", "D004"))
        self.assertEqual(len(packet.selected_ids), 20)
        self.assertEqual(packet.evidence_ids, packet.selected_ids)
        self.assertEqual(packet.omitted_diagnostics, 5)
        prompt_data = json.loads(packet.prompt.split("EVIDENCE_JSON:\n", 1)[1])
        self.assertEqual(prompt_data["coverage"]["selected_ids"], list(packet.selected_ids))

    def test_unstructured_failure_uses_bounded_process_evidence(self):
        run = self.make_run([], exit_code=101, non_json=("compiler wrapper failed",))
        run.artifacts.stdout_path.write_bytes(b"A" * 5000)
        run.artifacts.stderr_path.write_bytes(b"B" * 5000)
        packet = self.rd.build_analysis_packet(run, self.rd.normalize_diagnostics(run))
        self.assertEqual(packet.evidence_ids, ("cargo-process",))
        self.assertEqual(packet.selected_ids, ())
        self.assertLessEqual(len(packet.prompt.encode("utf-8")), 24 * 1024)
        evidence = json.loads(packet.prompt.split("EVIDENCE_JSON:\n", 1)[1])
        excerpt_bytes = sum(len(evidence["evidence"][0][name].encode("utf-8"))
                            for name in ("stdout_excerpt", "stderr_excerpt"))
        self.assertLessEqual(excerpt_bytes, 6 * 1024)

    def test_oversized_minimum_packet_skips_http(self):
        run = self.make_run([
            compiler_message("pkg", "lib", message="x" * (25 * 1024), spans=[]),
        ], exit_code=101)
        items = self.rd.normalize_diagnostics(run)
        with ollama_stub(self.rd) as requests:
            analysis = self.rd.analyze(run, items)
        self.assertEqual(analysis.status, "input_limit")
        self.assertEqual(requests, [])

    def test_optional_context_is_compacted_before_omitting_later_errors(self):
        large_optional = span(replacement=None)
        large_optional["text"] = [{
            "text": "x" * 23450, "highlight_start": 1, "highlight_end": 2}]
        run = self.make_run([
            compiler_message("pkg", "lib", message="first", code="E0001",
                             spans=[large_optional]),
            compiler_message("pkg", "lib", message="second", code="E0002",
                             spans=[span(replacement=None)]),
        ], exit_code=101)
        packet = self.rd.build_analysis_packet(run, self.rd.normalize_diagnostics(run))
        self.assertEqual(packet.selected_ids, ("D001", "D002"))

    def test_non_utf8_process_excerpts_use_encoded_six_kib_budget(self):
        run = self.make_run([], exit_code=101)
        run.artifacts.stdout_path.write_bytes(b"\xff" * 5000)
        run.artifacts.stderr_path.write_bytes(b"\xfe" * 5000)
        packet = self.rd.build_analysis_packet(run, self.rd.normalize_diagnostics(run))
        self.assertIsNotNone(packet)
        evidence = json.loads(packet.prompt.split("EVIDENCE_JSON:\n", 1)[1])
        excerpt_bytes = sum(len(evidence["evidence"][0][name].encode("utf-8"))
                            for name in ("stdout_excerpt", "stderr_excerpt"))
        self.assertLessEqual(excerpt_bytes, 6 * 1024)


class AnalysisTests(RunnerFixture):
    def ambiguous(self):
        run = self.make_run([
            compiler_message("pkg", "lib", spans=[span(replacement=None)]),
        ], exit_code=101)
        return run, self.rd.normalize_diagnostics(run)

    def test_request_uses_local_schema_and_validates_known_ids(self):
        run, items = self.ambiguous()
        with ollama_stub(self.rd) as requests, patch.dict(os.environ, {
                "HTTP_PROXY": "http://127.0.0.1:1",
                "QWEN_DIAGNOSTICS_MODEL": "local-diagnostics-model"}):
            analysis = self.rd.analyze(run, items)
        self.assertEqual(analysis.status, "ok")
        self.assertEqual(analysis.items[0]["evidence_ids"], ["D001"])
        self.assertEqual(len(requests), 1)
        path, payload, host, _port, method, headers = requests[0]
        self.assertEqual(path, "/api/generate")
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(method, "POST")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(payload["model"], "local-diagnostics-model")
        self.assertIs(payload["stream"], False)
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["options"], {"num_ctx": 32768, "num_predict": 1024})
        self.assertEqual(payload["format"]["properties"]["items"]["maxItems"], 3)

    def test_invalid_envelopes_and_unknown_ids_fall_back(self):
        run, items = self.ambiguous()
        cases = (
            {"done": False, "done_reason": "stop", "response": "{}"},
            {"done": True, "done_reason": "length", "response": "{}"},
            analysis_envelope([{"evidence_ids": ["D999"], "cause": "原因", "fix": "修正"}]),
            analysis_envelope([{"evidence_ids": [], "cause": "原因", "fix": "修正"}]),
            analysis_envelope([{"evidence_ids": ["D001"], "cause": 1, "fix": "修正"}]),
            analysis_envelope([{"evidence_ids": ["D001"], "cause": "原因",
                                "fix": "修正", "command": "cargo fix"}]),
            analysis_envelope([{"evidence_ids": ["D001"], "cause": "原因", "fix": "修正"}] * 4),
        )
        for response in cases:
            with self.subTest(response=response), ollama_stub(self.rd, response):
                analysis = self.rd.analyze(run, items)
            self.assertEqual(analysis.status, "invalid")

    def test_service_failures_preserve_fallback_statuses_without_retry(self):
        run, items = self.ambiguous()
        cases = ((0, b"", "unavailable"), (404, b"missing", "unavailable"),
                 (500, b"private server error", "unavailable"),
                 (200, b"not json", "invalid"),
                 (200, b"x" * (64 * 1024 + 1), "invalid"))
        for status, response, expected in cases:
            with self.subTest(status=status, expected=expected), \
                    ollama_stub(self.rd, response=response, status=status) as requests:
                analysis = self.rd.analyze(run, items)
            self.assertEqual(analysis.status, expected)
            self.assertEqual(len(requests), 1)

    def test_total_deadline_covers_delayed_and_dripping_responses(self):
        run, items = self.ambiguous()
        for options in ({"delay": 0.4}, {"drip": True}):
            with self.subTest(options=options), \
                    patch.object(self.rd, "REQUEST_TIMEOUT", 0.15), \
                    ollama_stub(self.rd, **options) as requests:
                started = time.monotonic()
                analysis = self.rd.analyze(run, items)
                elapsed = time.monotonic() - started
            self.assertEqual(analysis.status, "timeout")
            self.assertLess(elapsed, 0.35)
            self.assertEqual(len(requests), 1)

    def test_deterministic_results_do_not_contact_ollama(self):
        clean_run = self.make_run([], exit_code=0)
        clean = self.rd.normalize_diagnostics(clean_run)
        machine_run = self.make_run([
            compiler_message("pkg", "lib", spans=[span()]),
        ], exit_code=101)
        machine = self.rd.normalize_diagnostics(machine_run)
        with ollama_stub(self.rd) as requests:
            clean_analysis = self.rd.analyze(clean_run, clean)
            machine_analysis = self.rd.analyze(machine_run, machine)
        self.assertEqual(clean_analysis.status, "not_needed")
        self.assertEqual(machine_analysis.status, "not_needed")
        self.assertEqual(requests, [])


class OutputTests(RunnerFixture):
    def test_main_emits_one_bounded_line_and_returns_cargo_exit(self):
        with patch.dict(os.environ, {"FAKE_CARGO_MODE": "stream"}), \
                ollama_stub(self.rd, response=b"not json"):
            code, result, raw = self.main_output(["check", "--", "-p", "demo"])
        self.assertEqual(code, 101)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["cargo_exit_code"], 101)
        self.assertEqual(result["raw_error_count"], 1)
        self.assertEqual(result["unique_error_count"], 1)
        self.assertEqual(result["analysis_status"], "invalid")
        self.assertEqual(result["diagnostics"][0]["id"], "D001")
        self.assertEqual(result["diagnostics"][0]["code"], "E0308")
        self.assertTrue(Path(result["report_path"]).is_absolute())
        self.assertTrue(Path(result["report_path"]).exists())
        self.assertNotIn("private rendered output", raw)
        report = json.loads(Path(result["report_path"]).read_text())
        self.assertEqual(report["command"], [
            "cargo", "check", "-p", "demo", "--message-format=json", "--color=never"])

    def test_compaction_escapes_controls_and_retains_authoritative_fields(self):
        messages = [compiler_message(
            "pkg", "lib", level="error", message=("line\n\x1b[31m" + "界" * 5000),
            code="E0308", spans=[span(replacement="修正" * 1000)])
            for _ in range(4)]
        run = self.make_run(messages, exit_code=101)
        items = self.rd.normalize_diagnostics(run)
        analysis = self.rd.AnalysisResult(status="ok", items=tuple({
            "evidence_ids": ["D001"], "cause": "原因" * 2000,
            "fix": "修正" * 2000,
        } for _ in range(3)), coverage={
            "selected_ids": ["D001"], "omitted_diagnostics": 0,
            "stdout_excerpt_omitted": False, "stderr_excerpt_omitted": False,
        })
        report = self.rd.build_report(run, items, analysis)
        result = self.rd.compact_result(report)
        output = io.StringIO()
        with redirect_stdout(output):
            self.rd.emit_result(result)
        encoded = output.getvalue().encode("utf-8")
        self.assertLessEqual(len(encoded), 4096)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["cargo_exit_code"], 101)
        self.assertEqual(result["raw_error_count"], 4)
        self.assertEqual(result["analysis_status"], "ok")
        self.assertTrue(result["text_truncated"])
        self.assertNotIn(b"\x1b", encoded)

    def test_main_maps_argument_errors_without_tracebacks(self):
        code, result, raw = self.main_output(["build", "--"])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "execution_error")
        self.assertIsNone(result["cargo_exit_code"])
        self.assertEqual(result["code"], "INVALID_ARGUMENTS")
        self.assertNotIn("Traceback", raw)

    def test_main_maps_unexpected_failures_without_tracebacks(self):
        output = io.StringIO()
        with patch.object(self.rd, "run", side_effect=RuntimeError("private failure")), \
                redirect_stdout(output):
            code = self.rd.main(["check", "--"])
        raw = output.getvalue()
        result = json.loads(raw)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "execution_error")
        self.assertEqual(result["code"], "INTERNAL_ERROR")
        self.assertNotIn("private failure", raw)
        self.assertNotIn("Traceback", raw)


class RealRustTests(unittest.TestCase):
    def setUp(self):
        self.rd = load_runner()
        cargo = subprocess.run(["cargo", "--version"], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
        clippy = subprocess.run(["cargo", "clippy", "--version"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False)
        if cargo.returncode or clippy.returncode:
            self.skipTest("installed cargo and cargo-clippy are required")
        self.temp = tempfile.TemporaryDirectory(prefix="test-real-rust-diagnostics-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "src").mkdir()
        (self.root / "Cargo.toml").write_text(
            '[package]\nname = "diagnostic-fixture"\nversion = "0.1.0"\n'
            'edition = "2021"\n', encoding="utf-8")
        self.source = self.root / "src" / "main.rs"

    def execute(self, tool, source):
        self.source.write_text(source, encoding="utf-8")
        before = self.source.read_bytes()
        run = self.rd.run_cargo(
            self.rd.parse_argv([tool, "--", "--offline"]), self.root)
        items = self.rd.normalize_diagnostics(run)
        self.assertEqual(self.source.read_bytes(), before)
        return run, items

    def test_real_cargo_check_success_and_compile_failure(self):
        clean_run, clean = self.execute("check", 'fn main() { println!("ok"); }\n')
        self.assertEqual(clean_run.exit_code, 0)
        self.assertEqual(self.rd.execution_status(clean_run, clean), "passed")
        failed_run, failed = self.execute(
            "check", 'fn main() { let _value: u32 = "bad"; }\n')
        self.assertNotEqual(failed_run.exit_code, 0)
        self.assertGreaterEqual(failed.unique_error_count, 1)
        self.assertEqual(self.rd.execution_status(failed_run, failed), "failed")

    def test_real_clippy_warning_is_not_clean(self):
        run, items = self.execute(
            "clippy", "#![warn(clippy::eq_op)]\nfn main() { let _ = 1 == 1; }\n")
        self.assertEqual(run.exit_code, 0)
        self.assertGreaterEqual(items.unique_warning_count, 1)
        self.assertEqual(self.rd.execution_status(run, items), "warnings")


if __name__ == "__main__":
    unittest.main()
