from __future__ import annotations

import json
from pathlib import Path

from veridian_quant.v2 import run_cross_strategy_risk_diagnostic_audit


def test_cli_wires_defaultable_arguments(monkeypatch, tmp_path, capsys) -> None:
    observed = {}

    class FakeResult:
        output_dir = tmp_path / "out"
        outputs = {"risk_diagnostic_readme.txt": tmp_path / "out" / "risk_diagnostic_readme.txt"}
        metadata = {"caveat": "Read-only diagnostics only"}

    def fake_run(strategy_dirs, **kwargs):
        observed["strategy_dirs"] = strategy_dirs
        observed.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(
        run_cross_strategy_risk_diagnostic_audit,
        "run_cross_strategy_risk_diagnostic_audit",
        fake_run,
    )

    exit_code = run_cross_strategy_risk_diagnostic_audit.main(
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
            "--universe-csv",
            "universe.csv",
            "--classification-csv",
            "classification.csv",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert observed["strategy_dirs"]["S1"] == Path("s1")
    assert observed["strategy_dirs"]["S5"] == Path("s5")
    assert observed["output_dir"] == tmp_path / "out"
    assert observed["universe_csv"] == Path("universe.csv")
    assert observed["classification_csv"] == Path("classification.csv")
    assert payload["caveat"] == "Read-only diagnostics only"
