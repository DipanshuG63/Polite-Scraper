"""One-off manual robots.txt check for the explicitly authorized practice sandbox."""
import requests
from .main import USER_AGENT


def main() -> None:
    url = "https://books.toscrape.com/robots.txt"
    try:
        response = requests.get(url, timeout=10, allow_redirects=False, headers={"User-Agent": USER_AGENT})
    except requests.RequestException as exc:
        print(f"robots_url={url}\nrobots_result=unverified ({exc})")
        return
    print(f"robots_url={url}\nstatus={response.status_code}")
    if response.status_code == 404:
        print("robots_result=no robots file found (not blanket permission)")
    elif response.status_code == 200:
        print("robots_result=robots file found; review directives before making requests")
        print(response.text[:4000])
    else:
        print(f"robots_result=HTTP {response.status_code}; do not infer permission")


if __name__ == "__main__":
    main()
