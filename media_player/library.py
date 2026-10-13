"""Playlist storage compatible with the original single-column CSV format."""
import csv
from pathlib import Path
import random

MEDIA_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.wmv', '.m4v', '.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.ts', '.mpeg', '.mpg'}


def read_playlist(filename):
    filename = Path(filename)
    paths, missing = [], []
    with filename.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.reader(stream):
            if not row or not row[0].strip():
                continue
            path = Path(row[0])
            if not path.is_absolute():
                path = filename.parent / path
            path = path.resolve()
            if path.is_file():
                if str(path) not in paths:
                    paths.append(str(path))
            else:
                missing.append(str(path))
    return paths, missing


def write_playlist(filename, paths):
    filename = Path(filename)
    filename.parent.mkdir(parents=True, exist_ok=True)
    temporary = filename.with_suffix(filename.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        for entry in paths:
            path = Path(entry).resolve()
            # Relative paths keep media within a moved portable folder usable.
            try:
                import os
                value = os.path.relpath(path, filename.parent)
            except ValueError:
                value = str(path)
            writer.writerow([value])
    temporary.replace(filename)


class PlaybackQueue:
    def __init__(self):
        self.paths = []
        self.order = []
        self.current = None
        self.shuffled = False

    def replace(self, paths, current=None):
        self.paths = list(dict.fromkeys(paths))
        self.current = current if current in self.paths else (self.paths[0] if self.paths else None)
        self.set_shuffle(self.shuffled)

    def set_shuffle(self, enabled):
        self.shuffled = enabled
        self.order = self.paths.copy()
        if enabled:
            random.shuffle(self.order)
            if self.current in self.order:
                self.order.remove(self.current)
                self.order.insert(0, self.current)

    def step(self, direction, repeat=True):
        if not self.order:
            return None
        if self.current not in self.order:
            self.current = self.order[0]
            return self.current
        index = self.order.index(self.current) + direction
        if not repeat and not 0 <= index < len(self.order):
            return None
        self.current = self.order[index % len(self.order)]
        return self.current
