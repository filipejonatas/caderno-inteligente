from caderno_inteligente.auth import UserStore
from caderno_inteligente.dataset_store import Database, DatasetStore
from scripts.create_user import main as create_user
from scripts.import_workbook import main as import_workbook


def test_import_writes_every_sheet_once_and_requires_replace_afterwards(tmp_path, capsys):
    target = tmp_path / "dataset.db"
    assert import_workbook(["--sqlite", str(target)]) == 0
    assert "Importadas 13 abas" in capsys.readouterr().out
    assert import_workbook(["--sqlite", str(target)]) == 1
    assert "--replace" in capsys.readouterr().err
    assert import_workbook(["--sqlite", str(target), "--replace"]) == 0
    assert DatasetStore(Database(sqlite_path=target)).version() == 2


def test_import_refuses_a_missing_workbook(tmp_path, capsys):
    assert import_workbook(["--sqlite", str(tmp_path / "x.db"), "--source", str(tmp_path / "nao-existe.xlsm")]) == 1
    assert "Planilha não lida" in capsys.readouterr().err


def test_create_user_reads_the_password_from_the_environment(tmp_path, monkeypatch):
    target = tmp_path / "dataset.db"
    monkeypatch.setenv("CI_USER_PASSWORD", "senha-forte-123")
    assert create_user(["--email", "PCP@exemplo.com", "--name", "Ana", "--sqlite", str(target)]) == 0
    assert create_user(["--email", "pcp@exemplo.com", "--sqlite", str(target)]) == 1
    monkeypatch.setenv("CI_USER_PASSWORD", "outra-senha-456")
    assert create_user(["--email", "pcp@exemplo.com", "--reset-password", "--sqlite", str(target)]) == 0
    assert UserStore(Database(sqlite_path=target)).authenticate("pcp@exemplo.com", "outra-senha-456") is not None
    assert create_user(["--email", "ninguem@exemplo.com", "--reset-password", "--sqlite", str(target)]) == 1


def test_import_records_the_original_version_with_the_file_hash(tmp_path):
    import hashlib
    from caderno_inteligente.dataset_store import content_sha256
    from caderno_inteligente.ingestion import load_workbook
    from scripts.import_workbook import DEFAULT_SOURCE

    target = tmp_path / "dataset.db"
    assert import_workbook(["--sqlite", str(target)]) == 0
    store = DatasetStore(Database(sqlite_path=target))
    versions = store.list_versions()
    assert [(item["action"], item["user_email"], item["filename"]) for item in versions] == [("original", "script", DEFAULT_SOURCE.name)]
    assert versions[0]["file_sha256"] == hashlib.sha256(DEFAULT_SOURCE.read_bytes()).hexdigest()
    assert versions[0]["content_sha256"] == content_sha256(load_workbook(DEFAULT_SOURCE))
    assert store.state()["active_version_id"] == versions[0]["id"]


def test_import_accepts_xlsx_and_blocks_invalid_data_before_writing(tmp_path, capsys):
    import pandas as pd
    from caderno_inteligente.ingestion import load_workbook
    from scripts.import_workbook import DEFAULT_SOURCE

    dataset = load_workbook(DEFAULT_SOURCE)
    good = tmp_path / "base.xlsx"
    bad = tmp_path / "ruim.xlsx"
    for path, broken in ((good, False), (bad, True)):
        with pd.ExcelWriter(path) as writer:
            for sheet, frame in dataset.items():
                frame = frame.copy()
                if broken and sheet == "Carteira_Pedidos":
                    frame["Quantidade"] = frame["Quantidade"].astype(object)
                    frame.loc[frame.index[0], "Quantidade"] = "abc"
                frame.to_excel(writer, sheet_name=sheet, index=False, startrow=2)
    target = tmp_path / "dataset.db"
    assert import_workbook(["--sqlite", str(target), "--source", str(bad)]) == 1
    assert "nada foi gravado" in capsys.readouterr().err
    assert DatasetStore(Database(sqlite_path=target)).is_empty()
    assert import_workbook(["--sqlite", str(target), "--source", str(good)]) == 0
    assert DatasetStore(Database(sqlite_path=target)).list_versions()[0]["filename"] == "base.xlsx"
