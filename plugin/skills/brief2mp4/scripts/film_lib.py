"""film_lib.py: the small shared pieces of film mode: project paths, JSON files, errors.

Every film-mode script reads and writes plain files in one project folder, so any stage can be run alone:

    BRIEF.md -> STORY.md -> SCRIPT.md -> STORYBOARD.json -> ASSETS.json -> TIMINGS.json -> (retimed STORYBOARD.json)
             -> project/ (HyperFrames) -> audio/mix.wav -> final.mp4 + REPORT.md

Standard library only.
"""
from __future__ import annotations

import json
import os
import wave
from dataclasses import dataclass
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent


class FilmError(Exception):
    """A problem the user can fix. The message says what to do; film.py prints it as one FAIL line."""


@dataclass(frozen=True)
class Project:
    root: Path

    def p(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    @property
    def brief(self) -> Path: return self.p("BRIEF.md")
    @property
    def story(self) -> Path: return self.p("STORY.md")
    @property
    def script(self) -> Path: return self.p("SCRIPT.md")
    @property
    def storyboard(self) -> Path: return self.p("STORYBOARD.json")
    @property
    def assets(self) -> Path: return self.p("ASSETS.json")
    @property
    def timings(self) -> Path: return self.p("TIMINGS.json")
    @property
    def lines_dir(self) -> Path: return self.p("audio", "lines")
    @property
    def sfx_dir(self) -> Path: return self.p("assets", "sfx")
    @property
    def maps_dir(self) -> Path: return self.p("assets", "maps")
    @property
    def archive_dir(self) -> Path: return self.p("assets", "archive")
    @property
    def project(self) -> Path: return self.p("project")
    @property
    def mix(self) -> Path: return self.p("audio", "mix.wav")
    @property
    def final(self) -> Path: return self.p("final.mp4")
    @property
    def report(self) -> Path: return self.p("REPORT.md")

    def rel(self, path: Path | str) -> str:
        """A path as written in the stage files: relative to the project, forward slashes."""
        try:
            return Path(path).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return Path(path).as_posix()


def load_json(path: Path, what: str = "") -> dict | list:
    path = Path(path)
    if not path.is_file():
        raise FilmError(f"{what or path.name} not found at {path}: run the stage that writes it first")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as err:
        raise FilmError(f"{path.name} is not valid JSON ({err}): fix it or run its stage again")


def save_json(path: Path, data) -> None:
    """Write JSON as UTF-8 with LF endings, through a temp file so an interrupted run never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def frames(seconds: float, fps: float) -> int:
    return round(seconds * fps)
