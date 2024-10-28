from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse

from nested_data_helper.navigation import navigate
from scrapy import Spider
from scrapy.http import Request, Response, TextResponse


class RHSSpider(Spider):
    name: str = "rhs"

    separator: str = ","
    plants: Optional[str] = None

    def start_requests(self):
        if plants := self.plants:
            for plant in plants.split(self.separator):
                yield self.get_plant_search_request(plant)

    def get_plant_search_request(self, search_query):
        return Request(
            f"https://liveapi.yext.com/v2/accounts/me/answers/vertical/query?experienceKey=rhs-search&api_key=e37dcd85075611eaf5b95a155856af37&v=20220511&version=PRODUCTION&locale=en_GB&input={search_query}&verticalKey=plants&limit=50&offset=0&facetFilters=%7B%7D&session_id=bc73940c-828c-45e1-babe-8925e664b6e5&sessionTrackingEnabled=true&sortBys=%5B%5D&referrerPageUrl=https%3A%2F%2Fwww.rhs.org.uk%2F&source=STANDARD&jsLibVersion=v1.15.5",
            callback=self.parse_plant_search,
        )

    def parse_plant_search(self, response: TextResponse):
        """search_api:

        @url https://liveapi.yext.com/v2/accounts/me/answers/vertical/query?experienceKey=rhs-search&api_key=e37dcd85075611eaf5b95a155856af37&v=20220511&version=PRODUCTION&locale=en_GB&input=pear&verticalKey=plants&limit=50&offset=0&facetFilters=%7B%7D&session_id=bc73940c-828c-45e1-babe-8925e664b6e5&sessionTrackingEnabled=true&sortBys=%5B%5D&referrerPageUrl=https%3A%2F%2Fwww.rhs.org.uk%2F&source=STANDARD&jsLibVersion=v1.15.5
        @returns requests 51

        """
        data = response.json()

        for one in navigate(data, "response.results.[].data"):
            yield Request(
                one["landingPageUrl"],
                callback=self.parse_plant,
                meta={"api_result": data},
            )

        result_count: int = navigate(data, "response.resultsCount")

        query = dict(parse_qsl(urlparse(response.url).query))
        new_offset = int(query["offset"]) + int(query["limit"])

        if new_offset < result_count:
            query["offset"] = new_offset
            yield response.follow(
                "?" + urlencode(query), callback=self.parse_plant_search
            )

    def parse_plant(self, response: Response):
        """
        This function parses plant info from rhs.

        @url https://www.rhs.org.uk/plants/327466/brassica-oleracea-var-ramosa/details
        @returns items 1 1
        @returns requests 0 0
        @scrapes labels summary short_description ultimate_height time_to_ultimate_height ultimate_spread
        @scrapes soil_conditions moisture_conditions ph_conditions sun_conditions aspect_conditions
        @scrapes exposure_conditions hardiness colour_and_scents
        @scrapes family native_to_uk foliage habit genus_description name_status
        @scrapes cultivation propagation pruning pests diseases suggested_garden_type
        """
        plant = {"api_result": response.meta.get("api_result")}

        title = response.css("title::text").get()
        botanic_name, _ = title.split("|", 1)

        plant["botanic_name"] = botanic_name.strip()
        plant["genus"] = botanic_name.split(maxsplit=1)[0]
        plant["species"] = botanic_name.split(maxsplit=2)[1]

        plant["labels"] = response.css(".label::text").getall()
        plant["summary"] = response.css(".summary::text").get()
        plant["short_description"] = response.css(".summary+p::text").get()

        plant["ultimate_height"] = response.xpath(
            './/h6[contains(text(), "Ultimate height")]/../text()'
        ).get()
        plant["time_to_ultimate_height"] = response.xpath(
            './/h6[contains(text(), "Time to ultimate height")]/../text()'
        ).get()
        plant["ultimate_spread"] = response.xpath(
            './/h6[contains(text(), "Ultimate spread")]/../text()'
        ).get()

        def get_top_level_flags_from_plant_attr(title: str) -> list[str]:
            return (
                response.xpath(
                    f'.//*[@class="plant-attributes__header"][contains(.//text(), "{title}")]/'
                    "following-sibling::div"
                )
                .css(".flag__body::text")
                .getall()
            )

        def map_trim_or(strings: list[str]) -> list[str]:
            return [one.strip().replace(" or", "") for one in strings]

        plant["soil_conditions"] = get_top_level_flags_from_plant_attr(
            "Growing conditions"
        )

        plant["moisture_conditions"] = response.xpath(
            './/h6[contains(text(), "Moisture")]/../span/text()'
        ).getall()
        plant["ph_conditions"] = response.xpath(
            './/h6[contains(text(), "pH")]/../span/text()'
        ).getall()

        plant["sun_conditions"] = get_top_level_flags_from_plant_attr("Position")
        plant["aspect_conditions"] = map_trim_or(
            response.xpath(
                './/h6[contains(text(), "Aspect")]/following-sibling::p//span/text()'
            ).getall()
        )

        plant["exposure_conditions"] = map_trim_or(
            response.xpath(
                './/h6[contains(text(), "Exposure")]/following-sibling::span/text()'
            ).getall()
        )
        plant["hardiness"] = response.xpath(
            './/h6[contains(text(), "Hardiness")]/following-sibling::span/text()'
        ).getall()

        colour_scent_table = response.xpath(
            './/*[@class="plant-attributes__header"][contains(.//text(), "Colour & scent")]/'
            "following-sibling::div//table"
        )

        headers_row, *rows = colour_scent_table.xpath("tbody/tr")

        headers = headers_row.xpath("td/text()").getall()
        plant["colour_and_scents"] = {
            row.xpath("th/text()").get(): {
                header: list(map(str.strip, td.xpath(".//text()").getall()))
                for header, td in zip(headers, row.xpath("td"))
            }
            for row in rows
        }

        # Section: Botanical details
        def parse_botanical_details(title: str) -> str:
            element = response.xpath(f'.//dt[contains(text(), "{title}")]/..')
            if text := element.xpath("./dd/text()"):
                return text.get()
            if li := element.xpath("./dd/span/text()"):
                return [one.replace(", ", "") for one in li.getall()]
            return element.xpath("./dd/p/text()").get()

        plant["family"] = parse_botanical_details("Family")
        plant["native_to_uk"] = parse_botanical_details("Native to GB / Ireland")
        plant["foliage"] = parse_botanical_details("Foliage")
        plant["habit"] = parse_botanical_details("Habit")
        plant["genus_description"] = parse_botanical_details("Genus")
        plant["name_status"] = parse_botanical_details("Name status")

        # Section: How to grow
        def parse_how_to_grow(title: str) -> dict:
            p = response.xpath(
                f'.//h5[contains(text(), "{title}")]/following-sibling::p'
            )
            return {
                "html": p.get(),
                "links": [
                    {
                        "name": a.xpath("text()").get(),
                        "href": a.xpath("@href").get(),
                    }
                    for a in p.css("a")
                ],
            }

        plant["cultivation"] = parse_how_to_grow("Cultivation")
        plant["propagation"] = parse_how_to_grow("Propagation")
        plant["pruning"] = parse_how_to_grow("Pruning")
        plant["pests"] = parse_how_to_grow("Pests")
        plant["diseases"] = parse_how_to_grow("Diseases")
        plant["suggested_garden_type"] = response.xpath(
            './/h5[contains(text(), "Suggested planting locations and garden types")]'
            "/following-sibling::ul/li/text()"
        ).getall()

        yield plant
