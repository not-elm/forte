"""Behavioral tests; all Git mutations stay in disposable repositories."""
import importlib.util
from contextlib import contextmanager, redirect_stdout
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "qwen_commit.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("qwen_commit", RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def envelope(subject="fix: repair parser", body=""):
    return {"done": True, "done_reason": "stop",
            "response": json.dumps({"subject": subject, "body": body})}


@contextmanager
def ollama_stub(qc, response=None, status=200, callback=None, delay=0, drip=False):
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

        def request(self, _method, path, body, _headers):
            requests.append((path, json.loads(body)))
            if callback:
                callback()

        def getresponse(self):
            if status == 0:
                raise ConnectionResetError("disconnected")
            if delay or drip:
                waited = self.sock.closed.wait(delay if delay else 1.0)
                if waited:
                    raise OSError("closed by deadline")
            data = response if isinstance(response, bytes) else json.dumps(
                envelope() if response is None else response).encode()
            return FakeResponse(status, data)

        def close(self):
            if self.sock is not None:
                self.sock.closed.set()

    with patch.object(qc.http.client, "HTTPConnection", FakeConnection):
        yield requests


class RepositoryFixture(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RUNNER.exists(), "The local commit runner is not implemented")
        self.qc = load_runner()
        self.temp = tempfile.TemporaryDirectory(prefix="test-qwen-commit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT="0")
        self.env = patch.dict(os.environ, env, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.git("init", "-q")
        self.git("config", "user.name", "Qwen Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args, input_data=None):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              input=input_data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=True).stdout

    def stage(self, name, content):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content if isinstance(content, bytes) else content.encode())
        self.git("add", "--", name)

    def assert_code(self, code, action):
        with self.assertRaises(self.qc.CommitError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)


class RepositoryTests(RepositoryFixture):
    def test_prompt_uses_immutable_staged_snapshot(self):
        self.stage("example.txt", "staged marker\n")
        state = self.qc.snapshot(self.root)
        self.stage("example.txt", "subsequent staged marker\n")
        (self.root / "example.txt").write_text("unstaged marker\n")
        prompt = self.qc.build_prompt(state)
        self.assertIn("+staged marker", prompt)
        self.assertNotIn("subsequent staged marker", prompt)
        self.assertNotIn("unstaged marker", prompt)
        self.assertIsNone(state.head)

    def test_empty_index_is_rejected(self):
        self.assert_code("EMPTY_INDEX", lambda: self.qc.snapshot(self.root))
        self.stage("file", "base")
        self.git("commit", "-qm", "chore: initial")
        self.assert_code("EMPTY_INDEX", lambda: self.qc.snapshot(self.root))

    def test_non_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assert_code("INVALID_REPOSITORY", lambda: self.qc.snapshot(Path(temp)))

    def test_operations_are_rejected(self):
        self.stage("file", "new")
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD",
                       "rebase-merge", "rebase-apply", "sequencer"):
            with self.subTest(marker=marker):
                path = self.root / ".git" / marker
                path.touch()
                self.assert_code("UNSUPPORTED_STATE", lambda: self.qc.snapshot(self.root))
                path.unlink()

    def test_conflicts_are_rejected(self):
        blob = self.git("hash-object", "-w", "--stdin", input_data=b"data").strip()
        entries = b"".join(b"100644 " + blob + b" " + str(stage).encode() + b"\tfile\n"
                           for stage in (1, 2, 3))
        self.git("update-index", "--index-info", input_data=entries)
        self.assert_code("UNSUPPORTED_STATE", lambda: self.qc.snapshot(self.root))

    def test_oversized_prompt_is_rejected_without_truncation(self):
        self.stage("large", "x" * 25000)
        state = self.qc.snapshot(self.root)
        self.assert_code("INPUT_TOO_LARGE", lambda: self.qc.build_prompt(state))

    def test_binary_deletion_and_rename_metadata(self):
        self.stage("old", "rename marker\n")
        self.stage("deleted", "deletion marker\n")
        self.git("commit", "-qm", "chore: base")
        self.git("mv", "old", "new")
        self.git("rm", "deleted")
        self.stage("binary", b"\x00\xff\x01")
        prompt = self.qc.build_prompt(self.qc.snapshot(self.root))
        self.assertIn("Binary files", prompt)
        self.assertNotIn("GIT binary patch", prompt)
        self.assertIn("-deletion marker", prompt)
        self.assertIn("+rename marker", prompt)

    def test_external_diff_and_textconv_are_not_run(self):
        self.stage("file", "contents")
        self.git("config", "diff.external", "touch external-ran")
        self.git("config", "diff.test.textconv", "touch textconv-ran")
        self.stage(".gitattributes", "file diff=test\n")
        self.qc.build_prompt(self.qc.snapshot(self.root))
        self.assertFalse((self.root / "external-ran").exists())
        self.assertFalse((self.root / "textconv-ran").exists())


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.qc = load_runner()
        self.assertTrue(hasattr(self.qc, "generate_message"), "Generation is not implemented")

    def test_request_uses_local_schema_and_no_proxy(self):
        with ollama_stub(self.qc) as requests, patch.dict(os.environ, {
                "HTTP_PROXY": "http://127.0.0.1:1", "http_proxy": "http://127.0.0.1:1",
                "QWEN_COMMIT_MODEL": "local-test-model"}):
            message = self.qc.generate_message("private prompt")
        self.assertEqual(message, "fix: repair parser\n")
        self.assertEqual(len(requests), 1)
        path, payload = requests[0]
        self.assertEqual(path, "/api/generate")
        self.assertEqual(payload["model"], "local-test-model")
        self.assertEqual(payload["prompt"], "private prompt")
        self.assertIs(payload["stream"], False)
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["options"], {"num_ctx": 32768, "num_predict": 512})
        self.assertEqual(payload["format"]["required"], ["subject", "body"])

    def test_valid_body_and_breaking_scope(self):
        self.assertEqual(self.qc.validate_message(envelope(
            "feat(api)!: replace endpoint", "Explain the change.\n\nBREAKING CHANGE: new path.")),
            "feat(api)!: replace endpoint\n\nExplain the change.\n\nBREAKING CHANGE: new path.\n")

    def test_invalid_envelopes_and_messages_are_rejected(self):
        invalid = [None, [], {}, {**envelope(), "done": False},
                   {**envelope(), "done_reason": "length"},
                   {**envelope(), "response": "```json\n{}\n```"},
                   {**envelope(), "response": "{}"},
                   {**envelope(), "response": json.dumps({"subject": "fix: ok", "body": 5})}]
        invalid += [envelope(subject) for subject in
                    ("", "no type", "fix: ", "fix: one\ntwo", "fix: " + "x" * 100,
                     "fix: \x00hidden", "fix: \x1b[31mcolor", "fix: \u202ehidden",
                     "fix: one\u2028two", "fix: one\u2029two")]
        invalid += [envelope(body=body) for body in ("x" * 4096, "a\rb", "a\tb", "a\x00b")]
        for response in invalid:
            with self.subTest(response=response):
                with self.assertRaises(self.qc.CommitError) as caught:
                    self.qc.validate_message(response)
                self.assertEqual(caught.exception.code, "INVALID_RESPONSE")

    def test_http_errors_and_redirects_are_not_retried(self):
        for status in (302, 404, 500):
            with self.subTest(status=status), ollama_stub(self.qc, status=status) as requests:
                with self.assertRaises(self.qc.CommitError):
                    self.qc.generate_message("prompt")
                self.assertEqual(len(requests), 1)

    def test_invalid_and_oversized_http_bodies(self):
        for response in (b"not json", b"x" * (65536 + 1)):
            with self.subTest(length=len(response)), ollama_stub(self.qc, response):
                with self.assertRaises(self.qc.CommitError) as caught:
                    self.qc.generate_message("prompt")
                self.assertEqual(caught.exception.code, "INVALID_RESPONSE")

    def test_disconnected_service_is_unavailable(self):
        with ollama_stub(self.qc, status=0):
            with self.assertRaises(self.qc.CommitError) as caught:
                self.qc.generate_message("prompt")
        self.assertEqual(caught.exception.code, "OLLAMA_UNAVAILABLE")

    def test_deadline_covers_delayed_and_dripping_headers(self):
        for options in ({"delay": 0.3}, {"drip": True}):
            with self.subTest(options=options), ollama_stub(self.qc, **options) as requests:
                start = time.monotonic()
                with patch.object(self.qc, "REQUEST_TIMEOUT", 0.15):
                    with self.assertRaises(self.qc.CommitError) as caught:
                        self.qc.generate_message("prompt")
                self.assertEqual(caught.exception.code, "GENERATION_TIMEOUT")
                self.assertLess(time.monotonic() - start, 0.7)
                self.assertEqual(len(requests), 1)


class CommitTests(RepositoryFixture):
    def setUp(self):
        super().setUp()
        self.assertTrue(hasattr(self.qc, "run"), "Commit pipeline is not implemented")

    def hook(self, name, source):
        path = self.root / ".git" / "hooks" / name
        path.write_text("#!/bin/sh\n" + source)
        path.chmod(0o755)

    def main_output(self):
        output = io.StringIO()
        with patch.object(self.qc.Path, "cwd", return_value=self.root), redirect_stdout(output):
            code = self.qc.main([])
        text = output.getvalue()
        self.assertEqual(len(text.splitlines()), 1)
        self.assertLessEqual(len(text.encode()), 1024)
        return code, json.loads(text), text

    def main_output_args(self, argv):
        output = io.StringIO()
        with patch.object(self.qc.Path, "cwd", return_value=self.root), redirect_stdout(output):
            code = self.qc.main(argv)
        text = output.getvalue()
        self.assertEqual(len(text.splitlines()), 1)
        self.assertLessEqual(len(text.encode()), 1024)
        return code, json.loads(text), text

    def test_initial_commit_contains_only_staged_content(self):
        self.stage("file", "private staged marker\n")
        tree = self.git("write-tree").decode().strip()
        (self.root / "file").write_text("private unstaged marker\n")
        with ollama_stub(self.qc) as requests:
            code, result, output = self.main_output()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "committed")
        self.assertEqual(result["subject"], "fix: repair parser")
        self.assertEqual(result["hash"], self.git("rev-parse", "HEAD").decode().strip())
        self.assertEqual(self.git("rev-parse", "HEAD^{tree}").decode().strip(), tree)
        self.assertEqual(self.git("rev-list", "--count", "HEAD").strip(), b"1")
        self.assertEqual(self.git("show", "HEAD:file"), b"private staged marker\n")
        self.assertEqual((self.root / "file").read_text(), "private unstaged marker\n")
        self.assertNotIn("private", output)
        self.assertEqual(len(requests), 1)

    def test_normal_commit_preserves_parent_and_literal_shell_text(self):
        self.stage("file", "base")
        self.git("commit", "-qm", "chore: base")
        parent = self.git("rev-parse", "HEAD").strip()
        self.stage("file", "change")
        subject = "fix: preserve $(touch injected) and `touch injected2` literally"
        with ollama_stub(self.qc, envelope(subject)):
            self.qc.run(self.root)
        self.assertEqual(self.git("rev-parse", "HEAD^" ).strip(), parent)
        self.assertEqual(self.git("log", "-1", "--format=%s").decode().strip(), subject)
        self.assertFalse((self.root / "injected").exists())
        self.assertFalse((self.root / "injected2").exists())

    def test_index_change_during_generation_stops_commit(self):
        self.stage("file", "base")
        with ollama_stub(self.qc, callback=lambda: self.stage("file", "changed")):
            self.assert_code("REPOSITORY_CHANGED", lambda: self.qc.run(self.root))
        self.assertIsNone(self.qc.read_head(self.root))

    def test_head_change_during_generation_stops_commit(self):
        self.stage("file", "base")
        with ollama_stub(self.qc, callback=lambda: self.git("commit", "-qm", "chore: concurrent")):
            self.assert_code("REPOSITORY_CHANGED", lambda: self.qc.run(self.root))
        self.assertEqual(self.git("rev-list", "--count", "HEAD").strip(), b"1")
        self.assertEqual(self.git("log", "-1", "--format=%s").strip(), b"chore: concurrent")

    def test_failing_hook_is_honored_without_leaking_output(self):
        self.stage("file", "private staged marker")
        self.hook("pre-commit", "echo private-hook-log >&2\nexit 1\n")
        with ollama_stub(self.qc):
            code, result, output = self.main_output()
        self.assertEqual(code, 1)
        self.assertEqual(result["code"], "GIT_FAILURE")
        self.assertIs(result["committed"], False)
        self.assertNotIn("private", output)
        self.assertIsNone(self.qc.read_head(self.root))

    def test_hook_staging_more_content_reports_created_unexpected_commit(self):
        self.stage("file", "staged")
        self.hook("pre-commit", "echo extra > extra\ngit add extra\n")
        with ollama_stub(self.qc):
            code, result, _ = self.main_output()
        self.assertEqual(code, 1)
        self.assertEqual(result["code"], "UNEXPECTED_COMMIT")
        self.assertIs(result["committed"], True)
        self.assertEqual(self.git("rev-list", "--count", "HEAD").strip(), b"1")
        self.assertEqual(self.git("show", "HEAD:extra"), b"extra\n")

    def test_message_hook_subject_is_displayed_and_bounded(self):
        self.stage("file", "staged")
        actual = "fix: " + "x" * 2000
        self.hook("commit-msg", "printf '%s\\n' '" + actual + "' > \"$1\"\n")
        with ollama_stub(self.qc):
            code, result, _ = self.main_output()
        self.assertEqual(code, 0)
        self.assertIs(result["subject_truncated"], True)
        self.assertTrue(actual.startswith(result["subject"]))
        self.assertEqual(self.git("log", "-1", "--format=%s").decode().strip(), actual)

    def test_bad_generation_does_not_create_commit(self):
        self.stage("file", "private marker")
        with ollama_stub(self.qc, b"private raw server body") as requests:
            code, result, output = self.main_output()
        self.assertEqual(code, 1)
        self.assertEqual(result["code"], "INVALID_RESPONSE")
        self.assertIs(result["committed"], False)
        self.assertNotIn("private", output)
        self.assertEqual(len(requests), 1)
        self.assertIsNone(self.qc.read_head(self.root))

    def test_empty_index_does_not_contact_ollama(self):
        with ollama_stub(self.qc) as requests:
            code, result, _ = self.main_output()
        self.assertEqual(code, 1)
        self.assertEqual(result["code"], "EMPTY_INDEX")
        self.assertEqual(requests, [])

    def test_signed_commit_with_signature_display_verifies_successfully(self):
        key = self.root / "signing-key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        signers = self.root / "allowed-signers"
        signers.write_text("test@example.invalid " + key.with_suffix(".pub").read_text())
        self.git("config", "gpg.format", "ssh")
        self.git("config", "user.signingkey", str(key))
        self.git("config", "gpg.ssh.allowedSignersFile", str(signers))
        self.git("config", "commit.gpgsign", "true")
        self.git("config", "log.showSignature", "true")
        self.stage("file", "signed contents")
        with ollama_stub(self.qc):
            code, result, _ = self.main_output()
        self.assertEqual(code, 0, result)
        self.assertEqual(result["status"], "committed")
        self.assertIn(b"gpgsig -----BEGIN SSH SIGNATURE-----", self.git("cat-file", "commit", "HEAD"))

    def test_provided_message_skips_generation_and_large_diff_prompt(self):
        self.stage("large", "x" * 25000)
        message_path = self.root / "message.txt"
        message = ("fix: batch-fix 2 findings from api-review.md\n\n"
                   "Co-Authored-By: Claude <noreply@anthropic.com>\n")
        message_path.write_text(message, encoding="utf-8")
        with ollama_stub(self.qc) as requests:
            result = self.qc.run(self.root, message_file=message_path)
        self.assertEqual(requests, [])
        self.assertEqual(result["message_source"], "provided")
        commit = self.git("cat-file", "commit", "HEAD")
        self.assertEqual(commit.split(b"\n\n", 1)[1], message.encode())

    def test_provided_message_keeps_literal_shell_text(self):
        self.stage("file", "staged")
        message_path = self.root / "message.txt"
        message = "リリース準備 $(touch injected) and `touch injected2` literally\n"
        message_path.write_text(message, encoding="utf-8")
        self.qc.run(self.root, message_file=message_path)
        self.assertFalse((self.root / "injected").exists())
        self.assertFalse((self.root / "injected2").exists())
        self.assertEqual(self.git("cat-file", "commit", "HEAD").split(b"\n\n", 1)[1],
                         message.encode())

    def test_provided_message_honors_hooks_and_reports_no_commit(self):
        self.stage("file", "staged")
        message_path = self.root / "message.txt"
        message_path.write_text("fix: provided\n", encoding="utf-8")
        self.hook("pre-commit", "exit 1\n")
        with ollama_stub(self.qc) as requests:
            code, result, _ = self.main_output_args(
                ["--message-file", str(message_path)])
        self.assertEqual(code, 1)
        self.assertEqual(result["code"], "GIT_FAILURE")
        self.assertIs(result["committed"], False)
        self.assertEqual(requests, [])

    def test_provided_message_preserves_ssh_signing(self):
        key = self.root / "provided-signing-key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        signers = self.root / "provided-allowed-signers"
        signers.write_text("test@example.invalid " + key.with_suffix(".pub").read_text())
        self.git("config", "gpg.format", "ssh")
        self.git("config", "user.signingkey", str(key))
        self.git("config", "gpg.ssh.allowedSignersFile", str(signers))
        self.git("config", "commit.gpgsign", "true")
        self.git("config", "log.showSignature", "true")
        self.stage("file", "signed provided contents")
        message_path = self.root / "message.txt"
        message_path.write_text("署名付き変更\n", encoding="utf-8")
        result = self.qc.run(self.root, message_file=message_path)
        self.assertEqual(result["message_source"], "provided")
        self.assertIn(b"gpgsig -----BEGIN SSH SIGNATURE-----",
                      self.git("cat-file", "commit", "HEAD"))

    def test_generated_trailers_are_committed_in_order(self):
        self.stage("file", "staged")
        trailers = ["Co-Authored-By: Claude <noreply@anthropic.com>",
                    "Issue: R-RD-001"]
        with ollama_stub(self.qc) as requests:
            result = self.qc.run(self.root, trailers=trailers)
        self.assertEqual(len(requests), 1)
        self.assertEqual(result["message_source"], "qwen")
        self.assertEqual(
            self.git("cat-file", "commit", "HEAD").split(b"\n\n", 1)[1],
            ("fix: repair parser\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"
             "Issue: R-RD-001\n").encode(),
        )


class MessagePolicyTests(unittest.TestCase):
    def setUp(self):
        self.qc = load_runner()
        self.temp = tempfile.TemporaryDirectory(prefix="test-qwen-message-policy-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def assert_code(self, code, action):
        with self.assertRaises(self.qc.CommitError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def test_reads_utf8_message_up_to_64_kib(self):
        path = self.root / "message.txt"
        path.write_bytes(("é" * (64 * 1024 // 2)).encode("utf-8"))
        self.assertEqual(len(self.qc.read_provided_message(path).encode("utf-8")),
                         64 * 1024)
        path.write_bytes(b"x" * (64 * 1024 + 1))
        self.assert_code("INVALID_MESSAGE", lambda: self.qc.read_provided_message(path))

    def test_rejects_invalid_provided_messages(self):
        path = self.root / "message.txt"
        cases = (b"", b" \n\t", b"fix: bad\x00message", b"\xff")
        for content in cases:
            with self.subTest(content=content):
                path.write_bytes(content)
                self.assert_code("INVALID_MESSAGE",
                                 lambda: self.qc.read_provided_message(path))
        self.assert_code("INVALID_MESSAGE",
                         lambda: self.qc.read_provided_message(self.root / "missing"))

    def test_appends_validated_trailers_to_generated_message(self):
        message = self.qc.append_trailers(
            "fix: repair parser\n",
            ["Co-Authored-By: Claude <noreply@anthropic.com>", "Issue: R-RD-001"],
        )
        self.assertEqual(
            message,
            "fix: repair parser\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"
            "Issue: R-RD-001\n",
        )

    def test_rejects_invalid_trailers_and_oversized_final_message(self):
        cases = ("", "missing colon", ": value", "Key:", "Key: ",
                 "Key: first\nSecond: value", "Key: bad\x00value", " Key: value")
        cases += ("Key: first\u2028Second: value", "Key: first\u2029Second: value")
        for trailer in cases:
            with self.subTest(trailer=trailer):
                self.assert_code("INVALID_TRAILER",
                                 lambda trailer=trailer: self.qc.validate_trailer(trailer))
        self.assert_code(
            "INVALID_MESSAGE",
            lambda: self.qc.append_trailers("fix: repair parser\n", ["Key: " + "x" * 5000]),
        )

    def test_cli_modes_are_mutually_exclusive(self):
        self.assertEqual(
            self.qc.parse_cli(["--message-file", "message.txt"]),
            (Path("message.txt"), ()),
        )
        self.assertEqual(
            self.qc.parse_cli(["--trailer", "Issue: one", "--trailer", "Issue: two"]),
            (None, ("Issue: one", "Issue: two")),
        )
        self.assert_code(
            "INVALID_ARGUMENTS",
            lambda: self.qc.parse_cli([
                "--message-file", "message.txt", "--trailer", "Issue: one"]),
        )


if __name__ == "__main__":
    unittest.main()
