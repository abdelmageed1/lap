from PySide2.QtWidgets import QApplication
import sys

from app import db
from app.seed import seed_if_empty

def test_catalog_view_initializes(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_catalog_view.db"))
    db.init_schema()
    seed_if_empty()
    
    app = QApplication.instance() or QApplication(sys.argv)
    from app.ui.catalog_view import CatalogView
    view = CatalogView()
    assert view is not None
