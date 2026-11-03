"""The sound switch and the playSound hook survive without shipped clips.

No sound ships with the app any more: the reader's own clips replace the
generated tones. What has to stay is the engine (playSound and the audio
path it loads from) and the Sound setting, so a later sound library plugs
straight in without rewiring.
"""
import json
import unittest
from pathlib import Path

import accessible_ide
from accessible_ide import routes

ROOT = Path(accessible_ide.__file__).resolve().parent
APP_JS = (ROOT / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
TEMPLATE = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')

# The moments the app used to make a noise. Once a clip exists for one,
# playSound('name') is the hook that plays it.
SOUND_NAMES = ('press', 'success', 'error', 'pause')


class SoundEngineTest(unittest.TestCase):
    def test_the_engine_and_its_audio_path_exist(self):
        self.assertIn('function playSound(', APP_JS)
        self.assertIn('audio/', TEMPLATE)

    def test_named_moments_are_still_called_out_in_the_code(self):
        for name in SOUND_NAMES:
            self.assertIn("playSound('%s')" % name, APP_JS)

    def test_no_shipped_clips_are_left_behind(self):
        audio = ROOT / 'static' / 'audio'
        if audio.is_dir():
            self.assertEqual(list(audio.glob('*.wav')), [],
                             'shipped clips should be gone; use sfx files')


class SoundSettingTest(unittest.TestCase):
    def test_sound_is_on_by_default(self):
        self.assertIs(routes.DEFAULT_CONFIG['sound_enabled'], True)

    def test_sound_is_a_known_settings_key(self):
        self.assertIs(routes.CONFIG_TYPES['sound_enabled'], bool)

    def test_sound_can_be_saved_and_read_back(self):
        config = routes.DEFAULT_CONFIG.copy()
        config['sound_enabled'] = False
        self.assertIs(config['sound_enabled'], False)

    def test_the_switch_has_words_in_every_language(self):
        for code in ('en', 'fr', 'es', 'hi', 'ar', 'uk'):
            path = ROOT / 'i18n' / (code + '.json')
            data = json.loads(path.read_text(encoding='utf-8'))
            for key in ('group.sound', 'sound.label', 'sound.help'):
                self.assertTrue(data.get(key), '%s is missing %s' % (code, key))


if __name__ == '__main__':
    unittest.main()
