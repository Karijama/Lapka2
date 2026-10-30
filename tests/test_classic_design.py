"""Static regression tests: retain the original Jack/Bootstrap visual language."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_original_blue_navigation_and_bootstrap_tables():
    base = (ROOT / 'templates/base.html').read_text(encoding='utf-8')
    table = (ROOT / 'templates/_list_table.html').read_text(encoding='utf-8')
    assert 'navbar-dark bg-primary' in base
    assert 'display-5 fw-bold text-primary' in base
    assert 'breadcrumb' in base
    assert 'table table-hover table-striped' in table
    assert 'card-header bg-primary text-white' in table
    for heading in ('Дата создания', 'Заголовок', 'Содержание', 'Действия'):
        assert heading in table


def test_original_create_and_edit_card_headers():
    assert 'card-header bg-primary text-white' in (ROOT / 'templates/create.html').read_text(encoding='utf-8')
    assert 'card-header bg-warning text-dark' in (ROOT / 'templates/edit.html').read_text(encoding='utf-8')


def test_index_does_not_use_redesigned_card_gallery():
    index = (ROOT / 'templates/index.html').read_text(encoding='utf-8')
    assert "_list_table.html" in index
    assert 'pet-grid' not in index
