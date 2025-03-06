import re
from urllib.parse import urlencode
import math

from scrapy import Spider, Request
from scrapy.http import JsonResponse

from .xpaths import TOTAL_OFFERS_XPATH


class EtsturSpider(Spider):
    name = "etstur"
    base_url = "https://www.etstur.com"
    base_ajax_url = "https://www.etstur.com/ajax/hotel-search-load-more"
    base_city_url = "Akdeniz-Bolgesi-Otelleri"
    MAX_PAGE_ITEM_LIMIT = 20
    SCRAPED_PAGE_LIMIT = 1

    def __init__(
            self,
            adults: int,
            checkin_date: str,
            checkout_date: str,
            city: str = None,
            child_ages: str = None,
            **kwargs
    ) -> None:
        self.adults = adults
        self.checkin_date = checkin_date
        self.checkout_date = checkout_date
        self.city = city
        self.child_ages = child_ages

        

    @property
    def parsed_child_ages(self):
        if not self.child_ages:
            return
        child_age_list = self.child_ages.strip("-").split("-")
        child_params = {
            f"childage_1_{i + 1}": age for i, age in enumerate(child_age_list)
        }
        child_params.update({"child_1": len(child_age_list)})
        return child_params

    @property
    def params(self) -> dict:
        params = {
            "url": self.base_city_url,
            "check_in": self.checkin_date,
            "check_out": self.checkout_date,
            "adult_1": self.adults,
            "minPrice": 0,
            "maxPrice": 0,
            "sortType": "price",
            "sortDirection": "asc",
            "limit": self.MAX_PAGE_ITEM_LIMIT,
            "offset": 0,
        }
        if self.child_ages:
            params.update(self.parsed_child_ages)
        return params

    @property
    def base_url_with_params(self) -> str:
        start_params = self.params.copy()
        path = start_params.pop("url")
        url = f"{self.base_url}/{path}?{urlencode(start_params)}"
        return url

    def start_requests(self):
        if not self.city:
            url = self.base_url_with_params
            yield Request(url, callback=self.handle_pagination)
        else:
            url = f"https://www.etstur.com/v2/autocomplete?q={self.city}"
            yield Request(url, callback=self.handle_autocomplete)

    def handle_autocomplete(self, response: JsonResponse):
        data = response.json()
        path = data.get("result")[0].get("url")
        if self.base_city_url != path:
            self.base_city_url = path

        params = self.params.copy()
        del params["url"]
        url = f"{self.base_url}/{path}?{urlencode(params)}"
        yield Request(url, callback=self.handle_pagination)

    def handle_pagination(self, response):
        total_offers_string = response.xpath(TOTAL_OFFERS_XPATH).get()
        total_offers = int(re.findall(r'\d+', total_offers_string)[0])
        total_pages = math.ceil(total_offers / self.MAX_PAGE_ITEM_LIMIT)
        total_pages = total_pages if total_pages <= self.SCRAPED_PAGE_LIMIT else self.SCRAPED_PAGE_LIMIT  # noqa
        params = self.params.copy()

        for i in range(1, total_pages + 1):
            offset = i * self.MAX_PAGE_ITEM_LIMIT - 20
            params.update({"offset": offset})
            url = f"{self.base_ajax_url}?{urlencode(params)}"
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        print("\n\n\n", "im called", "\n\n\n")
