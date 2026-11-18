from django.test import TestCase, override_settings
from django.urls import reverse


class SearchIndexingTests(TestCase):
    def test_public_home_is_indexable_and_canonical(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="robots" content="index, follow"')
        self.assertContains(
            response,
            '<link rel="canonical" href="https://mavumba.pythonanywhere.com/">',
        )

    def test_account_pages_are_marked_noindex(self):
        response = self.client.get(reverse("account_login"))

        self.assertContains(response, 'name="robots" content="noindex, nofollow"')

    def test_legacy_home_url_canonicalizes_to_the_root(self):
        response = self.client.get(reverse("home-legacy"))

        self.assertContains(
            response,
            '<link rel="canonical" href="https://mavumba.pythonanywhere.com/">',
        )

    @override_settings(PUBLIC_SITE_DOMAIN="school.example")
    def test_sitemap_contains_only_the_public_homepage(self):
        response = self.client.get(reverse("sitemap"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://school.example/")
        self.assertNotContains(response, "/students/")
        self.assertNotContains(response, "/accounts/")

    @override_settings(PUBLIC_SITE_DOMAIN="school.example")
    def test_robots_txt_advertises_sitemap_and_excludes_private_routes(self):
        response = self.client.get(reverse("robots-txt"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(response, "Sitemap: https://school.example/sitemap.xml")
        for path in ("/admin/", "/students/", "/library/"):
            self.assertContains(response, f"Disallow: {path}")
