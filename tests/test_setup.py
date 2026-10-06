import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from construct_lab.setup import SetupStore, blank_settings
from construct_lab.server import make_server
from construct_lab.store import Conflict, Store


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "test.sqlite"
        self.s = SetupStore(self.path)
        self.s.seed_curiosity()
        self.pid = self.s.state()["projects"][0]["id"]

    def tearDown(self):
        self.s.close()
        self.directory.cleanup()

    def save(self, **overrides):
        args = dict(project=self.pid, expected_version=1, settings=blank_settings(),
                    actor="Test researcher", rationale="Synthetic test change")
        args.update(overrides)
        return self.s.save_configuration(**args)

    def test_settings_persist_and_seed_is_idempotent(self):
        settings = blank_settings()
        settings["research_question"] = "Synthetic research question"
        self.save(settings=settings)
        self.s.close()
        self.s = SetupStore(self.path)
        self.s.seed_curiosity()
        self.assertEqual(len(self.s.state()["projects"]), 1)
        project = self.s.project(self.pid)
        self.assertEqual(project["configuration"]["settings"], settings)
        self.assertEqual(project["configuration"]["version"], 2)
        self.assertEqual(project["definition_version"], 0)
        self.assertEqual(project["history"][1]["settings"]["phenomenon"], "Curiosity")
        self.assertEqual(project["configuration"]["status"], "draft")

    def test_two_connections_cannot_overwrite_a_new_version(self):
        other = SetupStore(self.path)
        try:
            self.save()
            before = self.s.export(self.pid)
            with self.assertRaises(Conflict):
                other.save_configuration(self.pid, 1, blank_settings(), "Other", "Stale")
            self.assertEqual(self.s.export(self.pid), before)
        finally:
            other.close()

    def test_template_copies_settings_without_evidence_or_approvals(self):
        source = self.s.add_source(self.pid, "Fixture", "p1", "Synthetic passage")
        claim = self.s.propose_claim(source, "Synthetic passage", "Interpretation")
        self.s.review_claim(claim, "Reviewer", "Test", True)
        self.s.approve_definition(self.pid, 0, "Synthetic definition", [claim], "Reviewer", "Test")
        settings = blank_settings()
        settings["domain"] = "Synthetic domain"
        self.save(settings=settings)
        tid = self.s.save_template(self.pid, 2, "Test template")
        self.save(expected_version=2)
        new = self.s.create_setup("New area", "Researcher", tid)
        self.assertEqual(new["configuration"]["settings"], settings)
        self.assertEqual(new["definition_version"], 0)
        result = self.s.export(new["id"])
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["claims"], [])
        self.assertEqual(result["revisions"], [])
        self.assertEqual(len(new["history"]), 1)
        self.s.save_configuration(new["id"], 1, blank_settings(), "Researcher", "Independent edit")
        another = self.s.create_setup("Third area", "Researcher", tid)
        self.assertEqual(another["configuration"]["settings"], settings)

    def test_invalid_configuration_rolls_back_without_events(self):
        before = self.s.export(self.pid)
        for bad in [-1, 0, True, 1.2, 10001, "2"]:
            settings = blank_settings()
            settings["minimum_batches"] = bad
            with self.assertRaises(ValueError):
                self.save(settings=settings)
        for settings in [{}, dict(blank_settings(), api_key="do not store secrets"), dict(blank_settings(), domain=[] )]:
            with self.assertRaises(ValueError):
                self.save(settings=settings)
        self.assertEqual(self.s.export(self.pid), before)

    def test_template_conflicts_and_missing_template_are_atomic(self):
        self.s.save_template(self.pid, 1, "Reusable")
        before = self.s.export(self.pid)
        with self.assertRaises(Conflict):
            self.s.save_template(self.pid, 1, "reusable")
        with self.assertRaises(Conflict):
            self.s.save_template(self.pid, 0, "Stale")
        with self.assertRaises(KeyError):
            self.s.create_setup("Missing", "Researcher", "missing-template")
        self.assertEqual(self.s.export(self.pid), before)
        self.assertEqual(len(self.s.state()["projects"]), 1)

    def test_existing_foundation_database_can_be_configured(self):
        old_path = Path(self.directory.name) / "old.sqlite"
        old = Store(old_path)
        pid = old.create_project("Existing research")
        old.close()
        migrated = SetupStore(old_path)
        try:
            migrated.seed_curiosity()
            self.assertEqual(len(migrated.state()["projects"]), 1)
            self.assertEqual(migrated.project(pid)["configuration"]["version"], 0)
            migrated.save_configuration(pid, 0, blank_settings(), "Researcher", "First setup")
            self.assertEqual(migrated.project(pid)["configuration"]["version"], 1)
        finally:
            migrated.close()


class LocalServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.server = make_server(Path(self.directory.name) / "http.sqlite", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.directory.cleanup()

    def request(self, path, data=None, headers=None):
        default = {"Origin": self.url, "Content-Type": "application/json", "X-Construct-Lab": "local"}
        if headers:
            default.update(headers)
        request = Request(self.url + path, data=json.dumps(data).encode() if data is not None else None, headers=default)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw

    def test_browser_endpoints_round_trip_and_export(self):
        status, html = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Research brief", html)
        _, state = self.request("/api/state")
        pid = state["projects"][0]["id"]
        status, result = self.request(f"/api/projects/{pid}/settings", dict(
            expected_version=1, settings=blank_settings(), actor="Researcher", rationale="Test"))
        self.assertEqual(status, 200)
        self.assertEqual(result["configuration"]["version"], 2)
        status, result = self.request(f"/api/projects/{pid}/templates", dict(expected_version=2, name="Reusable"))
        self.assertEqual(status, 200)
        status, new = self.request("/api/projects", dict(name="Independent", actor="Researcher", template_id=result["id"]))
        self.assertEqual(status, 200)
        status, exported = self.request(f"/api/projects/{new['id']}/export")
        self.assertEqual(status, 200)
        self.assertEqual(exported["schema_version"], 3)
        self.assertEqual(exported["literature"], [])
        self.assertEqual(exported["sources"], [])

    def test_cross_origin_and_rebinding_requests_are_blocked(self):
        data = dict(name="Bad request", actor="Test")
        self.assertEqual(self.request("/api/projects", data, {"Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.request("/api/projects", data, {"X-Construct-Lab": ""})[0], 403)
        self.assertEqual(self.request("/api/state", headers={"Host": "example.com"})[0], 403)

    def test_validation_conflicts_and_unknown_routes_have_useful_status(self):
        self.assertEqual(self.request("/api/projects", dict(name="", actor="Test"))[0], 400)
        self.assertEqual(self.request("/api/projects/missing")[0], 404)
        self.assertEqual(self.request("/unknown")[0], 404)
        _, state = self.request("/api/state")
        pid = state["projects"][0]["id"]
        payload = dict(expected_version=0, settings=blank_settings(), actor="Researcher", rationale="Stale")
        self.assertEqual(self.request(f"/api/projects/{pid}/settings", payload)[0], 409)


if __name__ == "__main__":
    unittest.main()
