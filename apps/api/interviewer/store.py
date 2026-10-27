from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

DEFAULTS = {
    "provider": "groq", "revision": 0,
    "providers": {
        "groq": {"live_model": "openai/gpt-oss-20b", "assessment_model": "openai/gpt-oss-120b", "live_route": "", "assessment_route": "", "paid_opt_in": False},
        "codex": {"live_model": "gpt-6-luna", "assessment_model": "gpt-6-luna", "live_route": "", "assessment_route": "", "paid_opt_in": False},
        "openrouter": {"live_model": "", "assessment_model": "", "live_route": "", "assessment_route": "", "paid_opt_in": False},
    },
}

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO migrations VALUES(1);
CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS resumes(id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, owner TEXT NOT NULL, revision INTEGER NOT NULL, active INTEGER NOT NULL, expires REAL NOT NULL, body TEXT NOT NULL);
DROP INDEX IF EXISTS one_active;
CREATE UNIQUE INDEX IF NOT EXISTS one_active_per_owner ON sessions(owner) WHERE active=1;
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, kind TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS requests(session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, key TEXT NOT NULL, fingerprint TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(session_id,key));
CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tombstones(id TEXT PRIMARY KEY, deleted REAL NOT NULL);
CREATE TABLE IF NOT EXISTS runner_cleanup(job_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, created REAL NOT NULL);
"""


def uid():
    return uuid.uuid4().hex


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class Conflict(Exception):
    pass


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript(SCHEMA)
            db.execute("INSERT OR IGNORE INTO settings VALUES(1,?)", (encode(DEFAULTS),))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA secure_delete=ON")
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def settings(self):
        with self.connect() as db:
            settings = json.loads(db.execute("SELECT body FROM settings WHERE id=1").fetchone()[0])
            settings["providers"].setdefault("codex", dict(DEFAULTS["providers"]["codex"]))
            return settings

    def get(self, sid, owner, db=None):
        if db is None:
            with self.connect() as connection:
                return self.get(sid, owner, connection)
        row = db.execute("SELECT body FROM sessions WHERE id=? AND owner=?", (sid, owner)).fetchone()
        if not row:
            raise KeyError(sid)
        return json.loads(row[0])

    def save(self, db, session, owner):
        changed = db.execute("UPDATE sessions SET revision=?,active=?,body=? WHERE id=? AND owner=?", (session["revision"], int(session["stage"] != "COMPLETED"), encode(session), session["id"], owner)).rowcount
        if changed != 1:
            raise KeyError(session["id"])

    def event(self, db, session, kind, payload):
        event = {**payload, "id": uid(), "kind": kind, "stage": session["stage"], "revision": session["revision"], "created": time.time()}
        db.execute("INSERT INTO events VALUES(?,?,?,?,?)", (event["id"], session["id"], kind, encode(event), event["created"]))
        return event

    def events(self, sid):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute("SELECT body FROM events WHERE session_id=? ORDER BY created,rowid", (sid,))]

    def queue_runner_cleanup(self, db, submission):
        # Legacy records have no dispatch marker; conservatively assume the
        # remote service may have accepted them until an administrator reconnects.
        if submission.get("remote_attempted") is not False:
            db.execute("INSERT OR IGNORE INTO runner_cleanup VALUES(?,?,?)", (submission["id"], submission["session_id"], time.time()))

    def expire(self):
        with self.transaction() as db:
            now = time.time()
            expired = [row[0] for row in db.execute("SELECT id,body,expires,active FROM sessions")
                       if row[2] < now or (not row[3] and json.loads(row[1]).get("retention") == "delete_on_close")]
            for sid in expired:
                for row in db.execute("SELECT body FROM submissions WHERE session_id=?", (sid,)).fetchall():
                    self.queue_runner_cleanup(db, json.loads(row[0]))
                db.execute("INSERT OR IGNORE INTO tombstones VALUES(?,?)", (sid, time.time()))
                db.execute("DELETE FROM sessions WHERE id=?", (sid,))
            db.execute("DELETE FROM resumes WHERE created<?", (now-86400,))
        return expired

    def recover(self):
        with self.transaction() as db:
            for row in db.execute("SELECT owner,body FROM sessions WHERE active=1").fetchall():
                session = json.loads(row[1])
                session["paused"] = True
                session["generation_id"] = uid()
                session["revision"] += 1
                for turn in session["turns"]:
                    if turn.get("delivery") == "generating":
                        turn["delivery"] = "interrupted"
                self.event(db, session, "recovery", {"reason": "Backend restarted; resume explicitly. No audio replay."})
                self.save(db, session, row[0])
            for row in db.execute("SELECT id,body FROM submissions").fetchall():
                body = json.loads(row[1])
                if body["status"] in ("queued", "running"):
                    self.queue_runner_cleanup(db, body)
                    body["status"] = "infrastructure_failure"
                    body["detail"] = ("Application restarted. Remote cancellation is pending; no automatic rerun. Retry explicitly after cleanup."
                                      if body.get("remote_attempted") is not False else
                                      "Application restarted before this attempt was dispatched. No code was executed. Retry explicitly.")
                    db.execute("UPDATE submissions SET body=? WHERE id=?", (encode(body), row[0]))
