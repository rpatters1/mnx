"""Validate notehead constraints against the schema generated from the metaspec.

Run from doctools with: python -m unittest discover -s tests
"""

import copy
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docgenerator.settings')

import django
django.setup()

from jsonschema import Draft202012Validator
from spectools.utils.jsonschema import make_json_schema


class NoteheadSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = make_json_schema()
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)
        path = Path(__file__).resolve().parents[1] / 'media/examples/json/hello-world.json'
        cls.document = json.loads(path.read_text())

    def with_head(self, head, kit=False, duration='quarter'):
        document = copy.deepcopy(self.document)
        part = document['parts'][0]
        event = part['measures'][0]['sequences'][0]['content'][0]
        event['duration']['base'] = duration
        if kit:
            part['kit'] = {'cymbal': {'staffPosition': 4}}
            event.pop('notes')
            event['kitNotes'] = [{'kitComponent': 'cymbal', 'notehead': head}]
        else:
            event['notes'][0]['notehead'] = head
        return document

    def test_shape_families_at_each_displayed_duration(self):
        for kit in (False, True):
            for shape in ('default', 'oval', 'x', 'diamond', 'triangle', 'slash', 'plus', 'circleX', 'square'):
                for duration in ('quarter', 'half', 'whole', 'breve'):
                    with self.subTest(kit=kit, shape=shape, duration=duration):
                        self.validator.validate(self.with_head({'shape': shape}, kit, duration))

    def test_independent_display_controls_and_glyphs(self):
        for kit in (False, True):
            for head in (
                {}, {'parentheses': True}, {'hide': True},
                {'shape': 'diamond', 'parentheses': True, 'hide': False},
                {'shape': 'x', 'glyph': 'noteheadXOrnateEllipse'},
                {'shape': 'custom', 'glyph': 'noteheadBlack'},
            ):
                with self.subTest(kit=kit, head=head):
                    self.validator.validate(self.with_head(head, kit))

    def test_invalid_heads(self):
        for kit in (False, True):
            for head in (
                {'shape': 'custom'}, {'glyph': 'noteheadBlack'},
                {'shape': 'normal'}, {'shape': 'cluster'}, {'shape': 'unknown'},
                {'size': 'cue'}, {'color': '#ff0000'},
                {'hide': 'true'}, {'parentheses': 1}, {'filled': True},
                {'unknown': True},
            ):
                with self.subTest(kit=kit, head=head):
                    self.assertFalse(self.validator.is_valid(self.with_head(head, kit)))

    def test_optional_enum_defaults(self):
        for slug, prop in (('notehead', 'shape'),):
            with self.subTest(slug=slug, prop=prop):
                attribute = self.schema['$defs'][slug]['properties'][prop]
                self.assertEqual(attribute['default'], 'default')
                definition = self.schema['$defs'][attribute['$ref'].split('/')[-1]]
                self.assertIn(attribute['default'], definition['enum'])

    def test_clusters_are_not_supported(self):
        document = copy.deepcopy(self.document)
        event = document['parts'][0]['measures'][0]['sequences'][0]['content'][0]
        event['noteheadClusters'] = [{'notes': ['lower', 'upper']}]
        self.assertFalse(self.validator.is_valid(document))

    def test_triangle_pointing(self):
        attribute = self.schema['$defs']['notehead']['properties']['pointing']
        self.assertEqual(attribute['default'], 'up')
        definition = self.schema['$defs'][attribute['$ref'].split('/')[-1]]
        self.assertIn(attribute['default'], definition['enum'])
        for kit in (False, True):
            for pointing in ('up', 'down'):
                for duration in ('quarter', 'half', 'whole', 'breve', 'longa', 'maxima', 'duplexMaxima'):
                    with self.subTest(kit=kit, pointing=pointing, duration=duration):
                        self.validator.validate(self.with_head(
                            {'shape': 'triangle', 'pointing': pointing}, kit, duration))
                self.validator.validate(self.with_head(
                    {'shape': 'triangle', 'pointing': pointing,
                     'glyph': 'noteheadTriangleDownBlack'}, kit))
            for shape in (None, 'default', 'oval', 'diamond', 'x', 'slash',
                          'plus', 'circleX', 'square', 'custom'):
                head = {'pointing': 'down'}
                if shape is not None:
                    head['shape'] = shape
                if shape == 'custom':
                    head['glyph'] = 'noteheadTriangleDownBlack'
                with self.subTest(kit=kit, head=head):
                    self.assertFalse(self.validator.is_valid(self.with_head(head, kit)))
            for pointing in ('auto', 'left', 'right', None, 1):
                with self.subTest(kit=kit, pointing=pointing):
                    self.assertFalse(self.validator.is_valid(self.with_head(
                        {'shape': 'triangle', 'pointing': pointing}, kit)))


if __name__ == '__main__':
    unittest.main()
