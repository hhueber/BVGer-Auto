import pandas as pd
from tqdm import tqdm
import time
import os
import re
from pprint import pprint
from typing import Tuple, Optional
from urllib.parse import urlparse, urljoin, parse_qs

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from langdetect import detect

BASE_URL = "https://bvger.weblaw.ch"
DOWNLOAD_FOLDER = "download"

# Test values
TEST_TARGET = "D-1234/2020"
TEST_LANG = "fr"
TEST_RANGE_COURT = {"D", "E"}
TEST_RANGE_NUMBERS = range(1, 21)
TEST_RANGE_YEARS = range(2023, 2024)

# Range
# 2*10000*18 = 360'000 hits
# 3 secs wait top, so ~ 13 days
# In reality, 51'822 hits
# 3 secs wait top, so ~ 2 days
court = {"D", "E"}
numbers = range(1, 10000)
years = range(2007, 2024)

options = Options()
options.headless = True


def get_bvger_page(target: str, lang="de", full_text=False, download=False, verbose=False):
    """
    Returns a specific page parameters.

    :param target: Link or ID of the BVGer, e.g., https://bvger.weblaw.ch/cache?id=46e9ba10-cb9b-4843-8031-b6e757a9c336 or 46e9ba10-cb9b-4843-8031-b6e757a9c336
    :param lang: Optional, lang for the research interface.
    :param full_text: Save the full text in the resulting dictionary. If `download` is True, the text is saved as a file instead.
    :param download: Download the PDF. If `full_text` is True, the text is saved as a file as well.
    :param verbose: Debug.
    :return:
    """
    driver = webdriver.Firefox(options=options)
    endpoint = urljoin(BASE_URL, "/cache?guiLanguage={lang}&id={target}")

    # Ensure that we only work with the target ID
    if BASE_URL in target:
        target = extract_bvger_cache_id(target)

    # Seek for the correct page
    target_endpoint = endpoint.format(lang=lang, target=target)
    if verbose:
        print(f"> Testing {target_endpoint}")
    driver.get(target_endpoint)

    try:
        # Wait for multiple elements to be present
        WebDriverWait(driver, 1).until(
            EC.presence_of_all_elements_located((By.ID, "customContentSegment"))
        )

        # Open all dropdowns
        dropdowns = driver.find_elements(By.CLASS_NAME, "accordionTitleCacheView")
        for dropdown in dropdowns:
            if "active" not in dropdown.get_attribute("class"):
                actual_dropdown = dropdown.find_element(By.CLASS_NAME, "accordionLabelSideContentCacheView")
                driver.execute_script("arguments[0].scrollIntoView();", actual_dropdown)
                ActionChains(driver).click(actual_dropdown).perform()

        # Click on "see more" buttons
        buttons = driver.find_elements(By.CLASS_NAME, "infiniteScrollerMoreOrLessButton")
        for button in buttons:
            driver.execute_script("arguments[0].scrollIntoView();", button)
            ActionChains(driver).click(button).perform()

        soup = BeautifulSoup(driver.page_source, 'html.parser')
    except Exception as e:
        if verbose:
            print("> Elements not found within the time frame")
            print(f"({str(e)})")
        soup = None
    finally:
        driver.quit()

    if soup:
        result = {
            "id": target,
            "link_page": target_endpoint,
            "query_lang": lang,
        }

        # Main content
        content = soup.find(id="customContentSegment")
        title = content.find(class_="ui header").text.split(" ")[1].strip()
        result["title"] = title
        if full_text:
            text = "\n".join(t.text for t in content.find_all("p"))
            if download:
                filename = f"{title.replace('/', '-')}.txt"
                with open(os.path.join(DOWNLOAD_FOLDER, "txt", filename), "w") as f:
                    f.write(text)
                result["full_text"] = None
                result["file_text"] = filename
            else:
                result["full_text"] = text
                result["file_text"] = None
        pdf = urljoin(BASE_URL, content.find("a", {"id": "idForTutorial"}, href=True)["href"])
        result["link_pdf"] = pdf
        if download:
            filename = f"{title.replace('/', '-')}.pdf"
            response = requests.get(pdf)
            with open(os.path.join(DOWNLOAD_FOLDER, "pdf", filename), "wb") as f:
                f.write(response.content)

            result["file_pdf"] = filename
        else:
            result["file_pdf"] = None

        # Side menu
        metadata = soup.find(id="sideMenuCacheViewAccordionComputer")
        opts = metadata.find_all(class_="generalGridRowCacheView")

        for opt in opts:
            key = opt.find(class_="title").text.strip()
            value = [label.text.strip() for label in opt.find_all(class_="label-wrapper")]
            result[key] = value

        if verbose:
            pprint(result)
        return result

    return None


def get_bvger_search(target: str, lang="de", verbose=False) -> Optional[str]:
    """
    Tries to find a specific page, and returns a link to the page and the pdf.

    :param target: ID of the BVGer, e.g., `A-1337/2002`.
    :param lang: Optional, lang for the research interface.
    :param verbose: Debug.
    :return: Link to the page if found, else None.
    """
    driver = webdriver.Firefox(options=options)
    endpoint = urljoin(BASE_URL, "/dashboard?guiLanguage={lang}&q=\"{target}\"")

    # Seek for the correct page
    target_endpoint = endpoint.format(lang=lang, target=target)
    if verbose:
        print(f"> Testing {target_endpoint}")
    driver.get(target_endpoint)

    try:
        # Wait for multiple elements to be present
        WebDriverWait(driver, 1).until(
            EC.presence_of_all_elements_located((By.ID, 'scrollerItem'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    except Exception as e:
        if verbose:
            print("> Elements not found within the time frame")
            print(f"({str(e)})")
        soup = None
    finally:
        driver.quit()

    if soup:
        # Get first scrollerItem
        scroller_item = soup.find(id="scrollerItem")

        # Get title and check if match
        title = scroller_item.find(class_="header").text
        if verbose:
            print("> Found: ", title)
        if not target in title:
            if verbose:
                print("> Target not corresponding!")
            return None

        links = scroller_item.find_all("a")
        page = None
        for link in links:
            link_relative = link["href"]
            if "cache" in link_relative:
                param = extract_bvger_cache_id(urljoin(BASE_URL, link_relative))
                page = urljoin(BASE_URL, f"cache?id={param}")

        if verbose:
            print(f"> Found page: {page}")
        return page

    return None


def extract_bvger_cache_id(link: str) -> Optional[str]:
    """
    Given a BVGer page, returns its ID.

    :param link: BVGer page.
    :return: ID or None.
    """
    page_url = urlparse(link)
    try:
        param = parse_qs(page_url.query)["id"][0]
    except KeyError:
        return None
    return param


# page, pdf = get_bvger_search(TEST_TARGET)
# get_bvger_page("https://bvger.weblaw.ch/cache?id=46e9ba10-cb9b-4843-8031-b6e757a9c336", verbose=True, full_text=True, download=True)

total = len(TEST_RANGE_COURT) * len(TEST_RANGE_NUMBERS) * len(TEST_RANGE_YEARS)
cur = 0
results = {}
for court in tqdm(TEST_RANGE_COURT):
    for num in tqdm(TEST_RANGE_NUMBERS, leave=False):
        for year in tqdm(TEST_RANGE_YEARS, leave=False):
            cur += 1
            target = f"{court}-{num}/{year}"
            page = get_bvger_search(
                target,
                lang=TEST_LANG,
                verbose=False,
            )
            if page:
                temp = get_bvger_page(
                    page,
                    lang=TEST_LANG,
                    full_text=True,
                    download=True,
                    verbose=False,
                )
                results[temp["id"]] = temp


df = pd.DataFrame.from_dict(results, orient="index")
df.to_excel(os.path.join(DOWNLOAD_FOLDER, "results.xlsx"))
