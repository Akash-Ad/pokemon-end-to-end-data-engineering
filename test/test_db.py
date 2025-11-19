import importlib
from pathlib import Path

def test_schema_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    import pokepipeline.config as cfg
    importlib.reload(cfg)
    import pokepipeline.db as db
    importlib.reload(db)
    import pokepipeline.models as models
    importlib.reload(models)

    db.create_schema()

    with db.session_scope() as s:
        s.add(models.Pokemon(
            id=999, name="specmon", base_experience=1,
            height_cm=100, weight_kg=10.0, bmi=10.0, sprite_url=None
        ))

    with db.session_scope() as s:
        row = s.get(models.Pokemon, 999)
        assert row is not None
        assert row.name == "specmon"

    db.drop_schema()
    assert Path(db_path).exists()