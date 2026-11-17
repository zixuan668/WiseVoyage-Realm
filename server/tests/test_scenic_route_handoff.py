import unittest
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2]/'.env')
from pydantic import ValidationError
from server.base.routers.tour_experience import ScenicDraftSettings, DraftSettingsInput, draft_settings_data


class SharedRouteSettingsTests(unittest.TestCase):
    def test_avoiding_steps_does_not_invent_an_elderly_passenger(self):
        data=draft_settings_data(ScenicDraftSettings(owner='test',spot_ids='[3,1]',avoid_steps=True,
            start_area='east',end_area='north'))
        self.assertEqual(data['spot_ids'],[3,1])
        self.assertTrue(data['avoid_steps']);self.assertTrue(data['few_steps'])
        self.assertFalse(data['elderly']);self.assertFalse(data['children'])
        self.assertEqual(data['start_area'],'east');self.assertEqual(data['end_area'],'north')

    def test_accessibility_from_children_is_separate_from_explicit_steps_preference(self):
        data=draft_settings_data(ScenicDraftSettings(owner='test',children=True))
        self.assertTrue(data['avoid_steps']);self.assertFalse(data['few_steps'])

    def test_invalid_gates_cannot_be_saved(self):
        with self.assertRaises(ValidationError):DraftSettingsInput(start_area='missing')
