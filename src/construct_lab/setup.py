"""Versioned project setup. Settings are draft research plans, never approvals."""
import json
from datetime import datetime, timezone
from uuid import uuid4

from .store import Store, Conflict, required


TEXT_FIELDS = (
    "phenomenon", "purpose", "domain", "level", "temporal_form", "research_question",
    "inclusion", "exclusion", "seed_papers", "search_terms", "literature_sources",
    "review_protocol", "stopping_protocol", "challenge_protocol", "resource_limits",
)
NUMBER_FIELDS = ("minimum_batches", "stable_batches")


def blank_settings():
    return dict({key: "" for key in TEXT_FIELDS}, **{key: None for key in NUMBER_FIELDS})


def validate_settings(value):
    if not isinstance(value, dict) or set(value) != set(blank_settings()):
        raise ValueError("Settings must contain exactly the supported research fields")
    result = {}
    for key in TEXT_FIELDS:
        if not isinstance(value[key], str) or len(value[key]) > 8000:
            raise ValueError("Research fields must be text of at most 8,000 characters")
        result[key] = value[key].strip()
    for key in NUMBER_FIELDS:
        n = value[key]
        if n is not None and (type(n) is not int or not 1 <= n <= 10000):
            raise ValueError("Batch counts must be whole numbers from 1 to 10,000, or blank")
        result[key] = n
    return result


def short_text(value):
    value = required(value)
    if len(value) > 200:
        raise ValueError("Names and attributions must be at most 200 characters")
    return value


class SetupStore(Store):
    def __init__(self, path):
        super().__init__(path)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS configuration_revisions(
          project TEXT NOT NULL REFERENCES projects(id), version INTEGER NOT NULL,
          settings TEXT NOT NULL, actor TEXT NOT NULL, rationale TEXT NOT NULL,
          created_at TEXT NOT NULL, PRIMARY KEY(project, version));
        CREATE TABLE IF NOT EXISTS configuration_templates(
          id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
          settings TEXT NOT NULL, source_project TEXT NOT NULL REFERENCES projects(id),
          source_version INTEGER NOT NULL, created_at TEXT NOT NULL);
        """)

    def _write_configuration(self, project, version, settings, actor, rationale):
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute("INSERT INTO configuration_revisions VALUES(?,?,?,?,?,?)",
                        (project, version, json.dumps(settings), actor, rationale, now))
        self.event(project, "configuration_saved", {"configuration_version": version,
                   "actor": actor, "rationale": rationale, "status": "draft"})

    def _configuration(self, project):
        row = self.db.execute("SELECT * FROM configuration_revisions WHERE project=? ORDER BY version DESC LIMIT 1",
                              (project,)).fetchone()
        if row is None:
            return {"version": 0, "settings": blank_settings(), "status": "draft"}
        item = dict(row)
        item["settings"] = json.loads(item["settings"])
        item["status"] = "draft"
        return item

    def project(self, project):
        row = self.db.execute("SELECT * FROM projects WHERE id=?", (project,)).fetchone()
        if row is None:
            raise KeyError("Project not found")
        history = []
        for r in self.db.execute("SELECT * FROM configuration_revisions WHERE project=? ORDER BY version DESC", (project,)):
            item = dict(r)
            item["settings"] = json.loads(item["settings"])
            history.append(item)
        return {"id": row["id"], "name": row["name"], "definition_version": row["version"],
                "configuration": self._configuration(project), "history": history}

    def state(self):
        projects = [dict(r) for r in self.db.execute("SELECT id,name FROM projects ORDER BY name,id")]
        templates = [dict(r) for r in self.db.execute(
            "SELECT id,name,source_version,created_at FROM configuration_templates ORDER BY name")]
        return {"projects": projects, "templates": templates}

    def create_setup(self, name, actor, template_id=None):
        name, actor = short_text(name), short_text(actor)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            settings = blank_settings()
            if template_id is not None:
                row = self.db.execute("SELECT settings FROM configuration_templates WHERE id=?", (required(template_id),)).fetchone()
                if row is None:
                    raise KeyError("Template not found")
                settings = json.loads(row["settings"])
            pid = str(uuid4())
            self.db.execute("INSERT INTO projects(id,name) VALUES(?,?)", (pid, name))
            self.event(pid, "project_created", {"name": name, "template_id": template_id})
            reason = "Created from a reusable template; review all settings for this domain" if template_id else "Created a blank research setup"
            self._write_configuration(pid, 1, settings, actor, reason)
        return self.project(pid)

    def save_configuration(self, project, expected_version, settings, actor, rationale):
        settings = validate_settings(settings)
        actor, rationale = short_text(actor), required(rationale)
        if len(rationale) > 8000 or type(expected_version) is not int or expected_version < 0:
            raise ValueError("A valid version and change reason are required")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.project(project)
            current = self._configuration(project)
            if current["version"] != expected_version:
                raise Conflict("Another save changed this project. Reload the latest settings before saving again; your text has been kept on screen.")
            self._write_configuration(project, expected_version + 1, settings, actor, rationale)
        return self.project(project)

    def save_template(self, project, expected_version, name):
        name = short_text(name)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.project(project)
            current = self._configuration(project)
            if type(expected_version) is not int or current["version"] != expected_version or expected_version < 1:
                raise Conflict("Save and reload the current project settings before creating a template")
            if self.db.execute("SELECT id FROM configuration_templates WHERE name=? COLLATE NOCASE", (name,)).fetchone():
                raise Conflict("A template with this name already exists; choose a different name")
            tid = str(uuid4())
            self.db.execute("INSERT INTO configuration_templates VALUES(?,?,?,?,?,?)",
                            (tid, name, json.dumps(current["settings"]), project, expected_version,
                             datetime.now(timezone.utc).isoformat()))
            self.event(project, "configuration_template_created", {"template_id": tid, "name": name,
                       "configuration_version": expected_version})
        return tid

    def seed_curiosity(self):
        # First launch only; existing projects and research choices are preserved.
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if self.db.execute("SELECT 1 FROM projects LIMIT 1").fetchone():
                return
            pid = str(uuid4())
            self.db.execute("INSERT INTO projects(id,name) VALUES(?,?)", (pid, "Curiosity"))
            self.event(pid, "project_created", {"name": "Curiosity"})
            settings = blank_settings()
            settings["phenomenon"] = "Curiosity"
            self._write_configuration(pid, 1, settings, "Initial setup",
                                      "User selected Curiosity; scope and research decisions remain open")

    def export(self, project):
        result = super().export(project)
        result["schema_version"] = 2
        result["configuration"] = self.project(project)
        return result
