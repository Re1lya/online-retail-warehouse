"""发布失败与同库并发的回归验证。"""
import pytest
from filelock import FileLock, Timeout
import pipeline


def test_failed_dbt_build_preserves_previous_database(tmp_path,monkeypatch):
    monkeypatch.setattr(pipeline,'ROOT',tmp_path)
    source=tmp_path/'source.xlsx';source.write_bytes(b'fixture')
    database=tmp_path/'warehouse.duckdb';database.write_bytes(b'previous database snapshot')
    monkeypatch.setattr(pipeline,'load_ods',lambda con,source: {'rows':0})
    def failed(*args):raise RuntimeError('dbt build rejected fixture')
    monkeypatch.setattr(pipeline,'run_dbt',failed)
    with pytest.raises(RuntimeError,match='rejected'):pipeline.run(source,database)
    assert database.read_bytes()==b'previous database snapshot'
    assert not database.with_suffix('.building.duckdb').exists()


def test_same_database_cannot_be_built_concurrently(tmp_path):
    database=tmp_path/'warehouse.duckdb'
    with FileLock(str(database)+'.lock'):
        with pytest.raises(Timeout):pipeline.run(tmp_path/'unused.xlsx',database)
