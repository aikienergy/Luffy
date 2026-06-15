"""Fail-loud instead of silent mocks (§Part4)."""
import pytest


def test_dataset_manager_raises_when_missing(tmp_path, monkeypatch):
    from src.data_engineering import dataset_manager as dm_mod
    dm = dm_mod.DatasetManager()
    dm.path = str(tmp_path / "does_not_exist.csv")
    with pytest.raises(FileNotFoundError):
        dm.load_static()


def test_design_engine_embedding_fails_loud_without_esm(monkeypatch):
    torch = pytest.importorskip("torch")  # skip if torch not installed
    pytest.importorskip("transformers")
    from src.ai_model.design_engine import DesignEngine
    de = DesignEngine.__new__(DesignEngine)  # avoid full init / disk loads
    de.esm_model = None
    de.tokenizer = None
    de._embed_cache = {}

    def boom():
        raise OSError("network blocked / weights unavailable")
    de._load_esm = boom
    with pytest.raises(RuntimeError):
        de._get_embedding("MMMMMMMMMM")
