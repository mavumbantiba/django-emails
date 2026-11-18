from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import reverse


class PublicSitemap(Sitemap):
    changefreq = "monthly"
    priority = 1.0
    protocol = "https"

    def items(self):
        return ["home"]

    def location(self, item):
        return reverse(item)

    def get_urls(self, page=1, site=None, protocol=None):
        canonical_site = Site(
            domain=settings.PUBLIC_SITE_DOMAIN,
            name="Kafunjo Secondary School",
        )
        return super().get_urls(
            page=page,
            site=canonical_site,
            protocol=self.protocol,
        )


def sitemap_xml(request):
    return sitemap(request, {"public": PublicSitemap()})


def robots_txt(request):
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /collections/",
            "Disallow: /library/",
            "Disallow: /parents/",
            "Disallow: /students/",
            "Disallow: /supplies/",
            f"Sitemap: https://{settings.PUBLIC_SITE_DOMAIN}/sitemap.xml",
            "",
        ]
    )
    return HttpResponse(content, content_type="text/plain")
