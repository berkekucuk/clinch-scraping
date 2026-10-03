import hashlib
import logging
import re
from curl_cffi import requests
from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)


class UFCStatsImpersonateMiddleware:

    def __init__(self):
        self.session = requests.Session(impersonate="chrome120")
        self.cookie_solved = False

    def _solve_challenge(self, initial_url: str) -> None:
        logger.info("[UFCSTATS MIDDLEWARE] Solving UFCStats JS challenge...")

        r1 = self.session.get(initial_url)
        nonce_match = re.search(r"nonce\s*=\s*[\x22\x27]([a-f0-9]+)[\x22\x27]", r1.text)
        if not nonce_match:
            return

        nonce = nonce_match.group(1)
        n = 0
        while True:
            candidate = f"{nonce}:{n}".encode("utf-8")
            h = hashlib.sha256(candidate).hexdigest()
            if h.startswith("00"):
                break
            n += 1

        logger.debug(f"[UFCSTATS MIDDLEWARE] Solved PoW! Nonce: {nonce}, n: {n}")
        r_post = self.session.post("http://ufcstats.com/__c", data={"nonce": nonce, "n": str(n)})

        if r_post.status_code in [200, 204]:
            self.cookie_solved = True
            logger.info("[UFCSTATS MIDDLEWARE] Successfully solved challenge and acquired session cookie.")
        else:
            logger.warning(f"[UFCSTATS MIDDLEWARE] Challenge POST status: {r_post.status_code}")

    def process_request(self, request, spider) -> HtmlResponse | None:
        if "ufcstats.com" not in request.url:
            return None

        try:
            if not self.cookie_solved or "_fmc" not in self.session.cookies.get_dict():
                self._solve_challenge(request.url)

            response = self.session.get(request.url)

            if "Checking your browser" in response.text:
                self.cookie_solved = False
                self._solve_challenge(request.url)
                response = self.session.get(request.url)

            resp_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ["content-encoding", "content-length"]
            }

            return HtmlResponse(
                url=request.url,
                status=response.status_code,
                headers=resp_headers,
                body=response.content,
                encoding="utf-8",
                request=request
            )

        except Exception as e:
            logger.error(f"[UFCSTATS MIDDLEWARE] Error fetching {request.url} with curl_cffi: {e}")
            return None
