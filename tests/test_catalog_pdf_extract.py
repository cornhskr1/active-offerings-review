import hashlib
import json
from pathlib import Path
import unittest
import tempfile
import shutil
import runpy
import sys
from unittest.mock import Mock, patch
from pypdf import PdfReader
import pdfplumber
from scripts.catalog_pdf_extract import extract_verified_page, validate_split_parents

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/catalog/menu-11.13.26.pdf'


class CatalogPdfTests(unittest.TestCase):
    def setUp(self):
        self.spatial = pdfplumber.open(FIXTURE)
        self.addCleanup(self.spatial.close)

    def test_official_fixture_and_every_page_preserve_source_characters(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                         '7b46c3e4cad0332107c8e21d46b92f40a350413a3a09a324cd7156815369f721')
        for i, page in enumerate(PdfReader(FIXTURE).pages, 1):
            self.assertTrue(extract_verified_page(page, self.spatial.pages[i-1], page_number=i).strip())

    def test_source_geometry_restores_cbi_afc_and_keeps_scope(self):
        pages = PdfReader(FIXTURE).pages
        lines = lambda i: [' '.join(x.split()) for x in extract_verified_page(pages[i-1], self.spatial.pages[i-1], page_number=i).splitlines()]
        self.assertIn('College Basketball Invitational (CBI) | Men | NO PLAYER PROPOSITION WAGERS', lines(20))
        self.assertIn('College Basketball Crown (CBC) | Men | NO PLAYER PROPOSITION WAGERS', lines(20))
        self.assertIn('AFC Champions League Elite | Men and Women', lines(27))
        self.assertIn('Roland-Garros / French Open | Men and Women', lines(41))
        self.assertNotIn('College Basketball Invitational (CBI) | Men and Women', lines(20))

    def test_offline_full_parser_and_basketball_restrictions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'scripts').mkdir()
            (root / 'data').mkdir()
            for name in ['update_catalog.py', 'refresh_ncaa_basketball_intelligence.py', 'athlete_age_evidence.py']:
                shutil.copy(ROOT / 'scripts' / name, root / 'scripts' / name)
            for name in ['catalog-season-map.json', 'ncaa-basketball.json', 'known-u18.json',
                         'ncaa-basketball-rules.json', 'ncaa-basketball-rosters.json']:
                shutil.copy(ROOT / 'data' / name, root / 'data' / name)
            webpage = Mock(text='<a href="https://nrgc.nebraska.gov/menu11.13.26.pdf">Nebraska Authorized Sports Wagering Menu 11.13.26</a>')
            pdf = Mock(content=FIXTURE.read_bytes())
            with patch('requests.get', side_effect=[webpage, pdf]), patch.object(sys, 'path', [str(ROOT / 'scripts')] + sys.path):
                runpy.run_path(str(root / 'scripts/update_catalog.py'), run_name='__main__')
                runpy.run_path(str(root / 'scripts/refresh_ncaa_basketball_intelligence.py'), run_name='__main__')
            catalog = json.loads((root / 'data/catalog-live.json').read_text())
            self.assertEqual('11.13.26', catalog['menu_version'])
            self.assertEqual(40, len(catalog['sections']))
            basketball = json.loads((root / 'data/ncaa-basketball-intelligence.json').read_text())
            self.assertEqual({'cbi', 'cbc'}, {r['id'] for r in basketball['catalog_special_rules']})
            self.assertTrue(basketball['collection_paused'])
            self.assertTrue(basketball['stale'])
            for rule in basketball['catalog_special_rules']:
                self.assertEqual('NO PLAYER PROPOSITION WAGERS', rule['restriction'])
                self.assertEqual('11.13.26', rule['catalog_version'])

    def test_character_loss_and_empty_pages_block(self):
        for plain, layout in [('NO PLAYER PROPOSITION WAGERS', 'PLAYER PROPOSITION WAGERS'), ('', '')]:
            page = Mock()
            page.extract_text.return_value = plain
            spatial = Mock()
            spatial.extract_text.return_value = layout
            with self.assertRaisesRegex(ValueError, 'review required'):
                extract_verified_page(page, spatial, page_number=1)

    def test_split_legal_parent_removal_or_gender_change_blocks(self):
        season = {'sports': [{'sport': 'Soccer', 'groups': [{'events': [
            {'catalog_event': 'AFC Champions League Elite | Men and Women',
             'coverage_children': [{'key': 'afc-men'}]}]}]}]}
        for text in ['A FC Champions League Elite | Men and Women', 'AFC Champions League Elite | Men']:
            with self.assertRaisesRegex(ValueError, 'legal parent missing'):
                validate_split_parents({'sections': [{'sport': 'Soccer', 'lines': [text]}]}, season)
        for suffix in ['', ' - NO PROPOSITION WAGERS', ' | NO PROPOSITION WAGERS']:
            validate_split_parents({'sections': [{'sport': 'Soccer', 'lines': [
                'AFC Champions League Elite | Men and Women' + suffix]}]}, season)


if __name__ == '__main__':
    unittest.main()
