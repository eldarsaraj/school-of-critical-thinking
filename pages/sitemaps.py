from django.contrib.sitemaps import Sitemap


class StaticSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return ["home", "families", "organizations", "learners", "articles", "about"]

    def location(self, item):
        return f"/{'' if item == 'home' else item + '/'}"
