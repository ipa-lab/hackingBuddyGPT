import os
import unittest

from hackingBuddyGPT.utils.openapi.openapi_parser import OpenAPISpecificationParser
from hackingBuddyGPT.utils.web_api.target_surface import (
    OpenAPISurface,
    SitemapSurface,
    TargetSurface,
    html_to_openapi,
    load_surface,
    parse_sitemap_xml,
    urls_to_openapi,
)

TEST_FILES = os.path.join(os.path.dirname(__file__), "test_files")
OAS_FILE = os.path.join(TEST_FILES, "oas", "test_oas.json")


class TestOpenAPISurface(unittest.TestCase):
    def test_from_file_lists_endpoints(self):
        surface = OpenAPISurface.from_file(OAS_FILE)
        endpoints = surface.get_endpoints()
        self.assertIn("/posts", endpoints)
        self.assertIn("get", endpoints["/posts"])
        # real spec carries schemas
        self.assertTrue(surface.get_schemas())

    def test_from_dict_matches_from_file(self):
        surface = OpenAPISurface.from_file(OAS_FILE)
        clone = OpenAPISpecificationParser.from_dict(surface.api_data)
        self.assertEqual(surface.get_endpoints(), clone.get_endpoints())

    def test_satisfies_protocol(self):
        surface = OpenAPISurface.from_file(OAS_FILE)
        self.assertIsInstance(surface, TargetSurface)
        self.assertFalse(surface.is_sitemap)


class TestSitemapConverters(unittest.TestCase):
    def test_urls_to_openapi(self):
        spec = urls_to_openapi(
            ["https://ex.com/", "https://ex.com/users", "https://ex.com/search?q=1&page=2"],
            host="https://ex.com",
        )
        self.assertEqual(set(spec["paths"]), {"/", "/users", "/search"})
        params = spec["paths"]["/search"]["get"]["parameters"]
        self.assertEqual({p["name"] for p in params}, {"q", "page"})

    def test_urls_filtered_by_host(self):
        spec = urls_to_openapi(["https://ex.com/a", "https://evil.com/b"], host="https://ex.com")
        self.assertEqual(set(spec["paths"]), {"/a"})

    def test_parse_sitemap_xml(self):
        xml = (
            '<?xml version="1.0"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<url><loc>https://ex.com/a</loc></url>"
            "<url><loc>https://ex.com/b?x=1</loc></url>"
            "</urlset>"
        )
        self.assertEqual(parse_sitemap_xml(xml), ["https://ex.com/a", "https://ex.com/b?x=1"])

    def test_billion_laughs_is_inert(self):
        # A malicious DTD must not be expanded; text extraction simply finds no <loc>.
        evil = (
            '<?xml version="1.0"?>'
            "<!DOCTYPE lolz [<!ENTITY lol \"lol\"><!ENTITY lol2 \"&lol;&lol;&lol;\">]>"
            "<urlset><url><loc>https://ex.com/ok</loc></url></urlset>"
        )
        self.assertEqual(parse_sitemap_xml(evil), ["https://ex.com/ok"])

    def test_html_to_openapi_links_and_forms(self):
        html = """
        <html><body>
          <a href="/about">about</a>
          <a href="https://other.com/x">external</a>
          <form action="/login" method="post">
            <input name="user"><input name="pass" required>
          </form>
        </body></html>
        """
        spec = html_to_openapi(html, base_url="https://ex.com", host="https://ex.com")
        self.assertIn("/about", spec["paths"])
        self.assertNotIn("/x", spec["paths"])  # external host dropped
        self.assertIn("post", spec["paths"]["/login"])
        params = spec["paths"]["/login"]["post"]["parameters"]
        names = {p["name"]: p for p in params}
        self.assertEqual(set(names), {"user", "pass"})
        self.assertTrue(names["pass"]["required"])


class TestSitemapSurface(unittest.TestCase):
    def test_surface_interface_parity(self):
        surface = SitemapSurface.from_urls(
            ["https://ex.com/users", "https://ex.com/admin/login"], host="https://ex.com"
        )
        self.assertIsInstance(surface, TargetSurface)
        self.assertTrue(surface.is_sitemap)
        # methods the testing phase relies on must work (schemas empty, no crash)
        self.assertIn("/users", surface.get_endpoints())
        self.assertEqual(surface.get_schemas(), {})
        self.assertIsNone(surface.get_schema_for_endpoint("/users", "get"))
        classes = surface.classify_endpoints("")
        # path-keyword classification still fires for a sitemap
        login_paths = [e["path"] for e in classes["login_endpoint"]]
        self.assertNotIn("/users", [e["path"] for e in classes["login_endpoint"]])
        self.assertIn("/admin/login", [e["path"] for cat in classes.values() for e in cat])


class TestLoadSurface(unittest.TestCase):
    def test_detects_openapi(self):
        self.assertIsInstance(load_surface(OAS_FILE), OpenAPISurface)

    def test_detects_sitemap(self, ):
        path = os.path.join(TEST_FILES, "_tmp_sitemap.txt")
        with open(path, "w") as handle:
            handle.write("https://ex.com/a\nhttps://ex.com/b\n")
        try:
            surface = load_surface(path, host="https://ex.com")
            self.assertIsInstance(surface, SitemapSurface)
            self.assertEqual(set(surface.get_endpoints()), {"/a", "/b"})
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
