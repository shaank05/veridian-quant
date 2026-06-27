from __future__ import annotations

import json
from pathlib import Path

from veridian_quant.v2 import run_cross_strategy_overlap_audit


def test_cli_wires_strategy_dirs_and_scope(monkeypatch, tmp_path, capsys) -> None:
    observed = {}

    class FakeResult:
        output_dir = tmp_path / "out"
        outputs = {"overlap_readme.txt": tmp_path / "out" / "overlap_readme.txt"}
        metadata = {"overlap_scope": "signals", "anchor_strategy": "S3"}

    def fake_run(strategy_dirs, **kwargs):
        observed["strategy_dirs"] = strategy_dirs
        observed.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(run_cross_strategy_overlap_audit, "run_cross_strategy_overlap_audit", fake_run)

    exit_code = run_cross_strategy_overlap_audit.main(
        [
            "--output-dir",
            str(tmp_path / "out"),
            "--s1-dir",
            "s1",
            "--s2-dir",
            "s2",
            "--s3-dir",
            "s3",
            "--s4-dir",
            "s4",
            "--s5-dir",
            "s5",
            "--anchor-strategy",
            "S3",
            "--lookback-days",
            "4",
            "--diagnostic-window-days",
            "2",
            "--top-n",
            "7",
            "--overlap-scope",
            "signals",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert observed["strategy_dirs"]["S1"] == Path("s1")
    assert observed["output_dir"] == tmp_path / "out"
    assert observed["anchor_strategy"] == "S3"
    assert observed["lookback_days"] == 4
    assert observed["diagnostic_window_days"] == 2
    assert observed["top_n"] == 7
    assert observed["overlap_scope"] == "signals"
    assert payload["overlap_scope"] == "signals"
