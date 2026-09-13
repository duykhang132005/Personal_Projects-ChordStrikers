import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.utils import prepare_song

RUNNER = Path(__file__).resolve().parent / "run_prepare_song.js"


def _js_prepare(text: str):
    if not shutil.which("node"):
        pytest.skip("node is required to compare the JS prepare_song port")
    result = subprocess.run(
        ["node", str(RUNNER), "--data-attr"],
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    "text",
    [
        "[C]Hello [G]world",
        "Chorus:\n[C]You are my sunshine, my [F]only sun[C]shine\n",
        "Verse 1:\nPlay [Am7] and [F#/A#]\n",
        "<script>alert(1)</script> [C] <img src=x onerror=alert(1)>\nDon't <b>xss</b>",
        "Intro\n[Bb]Flat [C#]sharp\n\n\nOutro:\n",
    ],
)
def test_js_prepare_song_matches_python(text):
    py_lines = [{"chord": str(c), "lyric": str(l)} for c, l in prepare_song(text, add_data_attr=True)]
    assert _js_prepare(text) == py_lines
