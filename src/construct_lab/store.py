"""Local persistence layer. Authentication belongs in the future service layer.

No AI output is treated as reviewed evidence. No saturation claim is inferred.
"""
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


class Conflict(ValueError):
    pass


def required(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A nonempty text value is required")
    return value.strip()


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS projects(
          id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sources(
          id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id),
          citation TEXT NOT NULL, locator TEXT NOT NULL, passage TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS claims(
          id TEXT PRIMARY KEY, source TEXT NOT NULL REFERENCES sources(id),
          quote TEXT NOT NULL, interpretation TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'proposed');
        CREATE TABLE IF NOT EXISTS revisions(
          id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id),
          version INTEGER NOT NULL, definition TEXT NOT NULL, evidence TEXT NOT NULL,
          reviewer TEXT NOT NULL, rationale TEXT NOT NULL,
          UNIQUE(project, version));
        CREATE TABLE IF NOT EXISTS events(
          seq INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL REFERENCES projects(id),
          kind TEXT NOT NULL, payload TEXT NOT NULL, occurred_at TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    def event(self, project, kind, payload):
        self.db.execute("INSERT INTO events(project,kind,payload,occurred_at) VALUES(?,?,?,?)",
                        (project, kind, json.dumps(payload), datetime.now(timezone.utc).isoformat()))

    def create_project(self, name):
        name = required(name)
        pid = str(uuid4())
        with self.db:
            self.db.execute("INSERT INTO projects(id,name) VALUES(?,?)", (pid, name))
            self.event(pid, "project_created", {"name": name})
        return pid

    def add_source(self, project, citation, locator, passage):
        values = tuple(required(x) for x in (citation, locator, passage))
        sid = str(uuid4())
        with self.db:
            self.db.execute("INSERT INTO sources VALUES(?,?,?,?,?)", (sid, project, *values))
            self.event(project, "source_added", {"source": sid})
        return sid

    def propose_claim(self, source, quote, interpretation):
        quote, interpretation = required(quote), required(interpretation)
        row = self.db.execute("SELECT * FROM sources WHERE id=?", (source,)).fetchone()
        if row is None or quote not in row["passage"]:
            raise ValueError("Quote must occur exactly in the stored source passage")
        cid = str(uuid4())
        with self.db:
            self.db.execute("INSERT INTO claims(id,source,quote,interpretation) VALUES(?,?,?,?)",
                            (cid, source, quote, interpretation))
            self.event(row["project"], "claim_proposed", {"claim": cid})
        return cid

    def review_claim(self, claim, reviewer, rationale, accept):
        reviewer, rationale = required(reviewer), required(rationale)
        if not isinstance(accept, bool):
            raise ValueError("Accept must be boolean")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT c.*, s.project FROM claims c JOIN sources s ON s.id=c.source WHERE c.id=?", (claim,)).fetchone()
            if row is None or row["status"] != "proposed":
                raise Conflict("Claim is missing or already reviewed")
            status = "verified" if accept else "rejected"
            self.db.execute("UPDATE claims SET status=? WHERE id=?", (status, claim))
            self.event(row["project"], "claim_reviewed", {"claim": claim, "status": status,
                       "reviewer": reviewer, "rationale": rationale})

    def approve_definition(self, project, expected_version, definition, evidence, reviewer, rationale):
        definition, reviewer, rationale = (required(x) for x in (definition, reviewer, rationale))
        evidence = list(dict.fromkeys(evidence))
        if not evidence:
            raise ValueError("A definition requires reviewed evidence")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT version FROM projects WHERE id=?", (project,)).fetchone()
            if row is None or row["version"] != expected_version:
                raise Conflict("Project version changed; review the current definition")
            for cid in evidence:
                claim = self.db.execute("SELECT c.status,s.project FROM claims c JOIN sources s ON c.source=s.id WHERE c.id=?", (cid,)).fetchone()
                if claim is None or claim["project"] != project or claim["status"] != "verified":
                    raise ValueError("Every evidence claim must be verified in this project")
            version = expected_version + 1
            rid = str(uuid4())
            self.db.execute("INSERT INTO revisions VALUES(?,?,?,?,?,?,?)",
                            (rid, project, version, definition, json.dumps(evidence), reviewer, rationale))
            self.db.execute("UPDATE projects SET version=? WHERE id=?", (version, project))
            self.event(project, "definition_approved", {"revision": rid, "version": version,
                       "reviewer": reviewer, "rationale": rationale})
        return version

    def export(self, project):
        row = self.db.execute("SELECT * FROM projects WHERE id=?", (project,)).fetchone()
        if row is None:
            raise ValueError("Unknown project")
        def records(sql):
            return [dict(r) for r in self.db.execute(sql, (project,))]
        return {"schema_version": 1, "research_status": "ongoing; saturation not assessed",
                "project": dict(row),
                "sources": records("SELECT * FROM sources WHERE project=? ORDER BY id"),
                "claims": records("SELECT c.* FROM claims c JOIN sources s ON s.id=c.source WHERE s.project=? ORDER BY c.id"),
                "revisions": records("SELECT * FROM revisions WHERE project=? ORDER BY version"),
                "events": records("SELECT * FROM events WHERE project=? ORDER BY seq")}
