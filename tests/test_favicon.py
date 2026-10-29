"""The page links an icon and the icon is served, so no load logs a 404."""

import pathlib
import tempfile
import unittest

from accessible_ide import create_app
from accessible_ide import routes


class FaviconTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_path = pathlib.Path(self._tmp.name)
        self._saved = {
            "CONFIG_DIR": routes.CONFIG_DIR,
            "CONFIG_FILE": routes.CONFIG_FILE,
            "ACCESS_CODE": routes.ACCESS_CODE,
        }
        routes.CONFIG_DIR = tmp_path
        routes.CONFIG_FILE = tmp_path / "config.json"
        routes.ACCESS_CODE = ""
        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.addCleanup(self._restore)

    def _restore(self):
        for key, value in self._saved.items():
            setattr(routes, key, value)
        self._tmp.cleanup()

    def test_the_page_links_the_icon(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('rel="icon"', body)
        self.assertIn("favicon.svg", body)

    def test_the_default_favicon_path_answers(self):
        # Browsers ask for /favicon.ico whether or not a link exists.
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/svg+xml")
        self.assertIn(b"<svg", response.get_data())
        response.close()


if __name__ == "__main__":
    unittest.main()
