import json
from caderno_inteligente.quality_report import write_quality_report

def test_writes_json_report(tmp_path):
    output = write_quality_report({"errors": [], "warnings": []}, tmp_path / "quality.json")
    assert json.loads(output.read_text(encoding="utf-8"))["errors"] == []
