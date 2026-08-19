
def extract_detail(container, label):
    val = container.xpath(f'.//strong[contains(text(), "{label}")]/following-sibling::span[1]/text()').get(default="").strip()
    return val if (val and val != 'N/A') else None


def extract_reach(container):
    val = container.xpath('.//strong[contains(text(), "Reach")]/ancestor::div/following-sibling::div[1]/span/text()').get(default="").strip()
    return val if val else None
