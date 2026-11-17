# Stage 0: target classification

Target: Books to Scrape — https://books.toscrape.com/

Books to Scrape is an explicitly designated web-scraping practice sandbox
(https://sites.toscrape.com/). This project targets only the first three
catalogue pages, collecting eight raw fields + numeric GBP price from their
60 book links. It does not scrape other websites or follow off-domain URLs.

Historical public sources have reported HTTP 404 for /robots.txt (no robots
file found). This run environment could not verify a fresh result. A missing
file is not permission; the sandbox's own published description is the
reason to use this site. Run `python -m src.classify` to check current robots.

I will not reuse this code on another site without checking its rules and terms first.
