import datetime
import sys
import argparse
import re
from pathlib import Path

import pandas as pd
from tqdm import tqdm
import os
from pprint import pprint
from typing import Optional
from urllib.parse import urlparse, urljoin, parse_qs

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver import ChromeOptions, FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://bvger.weblaw.ch"
BASE_DOWNLOAD_FOLDER = "download"

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
MAX_COURTS = {"A", "B", "C", "D", "E", "F"}
MAX_YEARS = range(2007, datetime.datetime.now().year + 1)
MAX_NUMBERS = range(1, 10000)

PATTERN = re.compile(r"^([A-F])\-([1-9]|[1-9]\d{1,3})\/(200[7-9]|201\d|202[0-4])$")

LANGS = {"de", "fr", "it"}

chrome_options = ChromeOptions()
chrome_options.add_argument("--headless=new")
firefox_options = FirefoxOptions()
firefox_options.add_argument("-headless")


def get_bvger_page(target: str, lang="de", full_text=False, download=False, download_folder=BASE_DOWNLOAD_FOLDER,
                   verbose=False):
    """
    Returns a specific page parameters.

    :param target: Link or ID of the BVGer, e.g., https://bvger.weblaw.ch/cache?id=46e9ba10-cb9b-4843-8031-b6e757a9c336 or 46e9ba10-cb9b-4843-8031-b6e757a9c336
    :param lang: Optional, lang for the research interface.
    :param full_text: Save the full text in the resulting dictionary. If `download` is True, the text is saved as a file instead.
    :param download: Download the PDF. If `full_text` is True, the text is saved as a file as well.
    :param download_folder: Download folder.
    :param verbose: Debug.
    :return:
    """
    try:
        driver = webdriver.Firefox(options=firefox_options)
        endpoint = urljoin(BASE_URL, "/cache?guiLanguage={lang}&id={target}")

        # Ensure that we only work with the target ID
        if BASE_URL in target:
            target = extract_bvger_cache_id(target)

        # Seek for the correct page
        target_endpoint = endpoint.format(lang=lang, target=target)
        if verbose:
            print(f"> Testing {target_endpoint}")
        driver.get(target_endpoint)
    except Exception as e:
        print(f"Error with Selenium: {e}")
        return None

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
        try:
            result = {
                "id": target,
                "link_page": target_endpoint,
                "query_lang": lang,
            }

            # Main content
            content = soup.find(id="customContentSegment")
            title = content.find(class_="ui header").text.split(" ")[1].strip()
            result["title"] = title
            result["full_text"] = None
            result["file_text"] = None
            if full_text:
                text = "\n".join(t.text for t in content.find_all("p"))
                if download:
                    filename = f"{title.replace('/', '-')}.txt"
                    with open(os.path.join(download_folder, "txt", filename), "w") as f:
                        f.write(text)
                    result["file_text"] = filename
                else:
                    result["full_text"] = text
            pdf = urljoin(BASE_URL, content.find("a", {"id": "idForTutorial"}, href=True)["href"])
            result["link_pdf"] = pdf
            result["file_pdf"] = None
            if download:
                filename = f"{title.replace('/', '-')}.pdf"
                response = requests.get(pdf)
                with open(os.path.join(download_folder, "pdf", filename), "wb") as f:
                    f.write(response.content)

                result["file_pdf"] = filename

            # Side menu
            metadata = soup.find(id="sideMenuCacheViewAccordionComputer")
            opts = metadata.find_all(class_="generalGridRowCacheView")

            for opt in opts:
                key = opt.find(class_="title").text.strip()
                value = ";".join([label.text.strip() for label in opt.find_all(class_="label-wrapper")])
                result[key] = value

            if verbose:
                pprint(result)
            return result
        except Exception as e:
            print(f"Error with {target}: {str(e)}")
            return None

    return None


def get_bvger_search(target: str, lang="de", verbose=False) -> Optional[str]:
    """
    Tries to find a specific page, and returns a link to the page and the pdf.

    :param target: ID of the BVGer, e.g., `A-1337/2002`.
    :param lang: Optional, lang for the research interface.
    :param verbose: Debug.
    :return: Link to the page if found, else None.
    """
    try:
        driver = webdriver.Firefox(options=firefox_options)
        endpoint = urljoin(BASE_URL, "/dashboard?guiLanguage={lang}&q=\"{target}\"")

        # Seek for the correct page
        target_endpoint = endpoint.format(lang=lang, target=target)
        if verbose:
            print(f"> Testing {target_endpoint}")
        driver.get(target_endpoint)
    except Exception as e:
        print(f"Error with Selenium: {e}")
        return None

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
        try:
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
        except Exception as e:
            print(f"Error with {target}: {str(e)}")
            return None

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


def check_and_get_ranges(inpt: str, num_min: int, num_max: int, name: str):
    temp_numbers = inpt.split(";")
    numbers = []
    for num in temp_numbers:
        if "-" in num:
            a, b = num.split("-")
            try:
                a = int(a)
                b = int(b)
            except ValueError:
                raise ValueError(f"Incorrect {name} in input (`{a}`, `{b}`)")
            if a < num_min:
                raise ValueError(f"Incorrect {name} in input (`{a}` < `{num_min}`)")
            if b > num_max:
                raise ValueError(f"Incorrect {name} in input (`{b}` > `{num_max}`)")
            numbers.extend(range(a, b + 1))
        else:
            try:
                num = int(num)
            except ValueError:
                raise ValueError(f"Incorrect {name} in input (`{num}`)")
            if num < num_min:
                raise ValueError(f"Incorrect {name} in input (`{num}` < `{num_min}`)")
            if num > num_max:
                raise ValueError(f"Incorrect {name} in input (`{num}` > `{num_max}`)")
            numbers.append(num)
    return sorted(set(numbers))


# page, pdf = get_bvger_search(TEST_TARGET)
# get_bvger_page("https://bvger.weblaw.ch/cache?id=46e9ba10-cb9b-4843-8031-b6e757a9c336", verbose=True, full_text=True, download=True)

if __name__ == "__main__":
    # General parser
    parser = argparse.ArgumentParser(
        prog="BVGer Auto",
        description="Crawler for BVGer",
        epilog="Remember, be excellent to each others"
    )
    parser.add_argument("-l", "--query-lang",
                        help="Lang for the research interface",
                        default="de")
    parser.add_argument("-v", "--verbose",
                        help="Debug",
                        action="store_true")
    parser.add_argument("-f", "--full-text",
                        help="Save the full text in the resulting dictionary. If `download` is True, the text is saved as a file instead",
                        action="store_true")
    parser.add_argument("-d", "--download",
                        help="Download the PDF. If `full_text` is True, the text is saved as a file as well",
                        action="store_true")
    parser.add_argument("-o", "--download-folder",
                        help="Where the result will be saved (default `./download`)",
                        default=BASE_DOWNLOAD_FOLDER)
    subparsers = parser.add_subparsers(help="`page` for a specific page, `collect` for multiple pages")

    # Page subparser
    parser_page = subparsers.add_parser("page",
                                        help="Search and return a specific page")
    parser_page.add_argument("title",
                             help="Specific page title (\"D-1234/2020\")")

    # Search subparser
    parser_collect = subparsers.add_parser("collect",
                                           help="Search and return multiple pages")

    parser_collect.add_argument("courts",
                                help="Courts to be used for collection, either a single letter (A), or multiple letters (\"A;F\")")
    parser_collect.add_argument("years",
                                help="Years to be used for collection, either a single year (2007), or multiple years (\"2007;2025\"), or a range (\"2007-2025\")")
    parser_collect.add_argument("numbers",
                                help="Numbers to be used for collection, either a single number (1), or multiple numbers (\"1;9999\"), or a range (\"1-9999\")")

    args = parser.parse_args()

    # Check that the query lang is valid
    query_lang = args.query_lang
    if query_lang not in LANGS:
        sys.stderr.write(f"Incorrect lang in input (`{query_lang}`) not in `{', '.join(sorted(LANGS))}`\n")
        exit(-1)

    # Check and/or create download folder
    download_folder = args.download_folder
    Path(download_folder).mkdir(parents=True, exist_ok=True)
    Path(download_folder, "pdf").mkdir(parents=True, exist_ok=True)
    Path(download_folder, "txt").mkdir(parents=True, exist_ok=True)

    # Other arguments
    full_text = args.full_text
    download = args.download
    verbose = args.verbose

    if "title" in args:
        title = args.title

        if not PATTERN.match(title):
            sys.stderr.write(f"Incorrect title in input (`{title}`)\n")
            exit(-1)

        page = get_bvger_search(
            title,
            lang=query_lang,
            verbose=verbose,
        )
        if page:
            temp = get_bvger_page(
                page,
                lang=query_lang,
                full_text=full_text,
                download=download,
                download_folder=download_folder,
                verbose=verbose,
            )

            if temp:
                df = pd.DataFrame.from_dict(temp, orient="index")
                df.to_excel(os.path.join(download_folder, f"{title.replace('/', '-')}.xlsx"))
                sys.stdout.write(f"Found: `{title}`\n")
            else:
                sys.stdout.write(f"Eror with `{title}`\n")
        else:
            sys.stdout.write(f"Not found: `{title}`\n")
    elif "courts" in args:
        # Split the courts input and check that it is valid
        courts = args.courts.split(";")
        for court in courts:
            if court not in MAX_COURTS:
                sys.stderr.write(f"Incorrect court in input (`{court}`) not in `{', '.join(sorted(MAX_COURTS))}`\n")
                exit(-1)

        # Split the years input and check that it is valid
        years = check_and_get_ranges(args.years, MAX_YEARS[0], MAX_YEARS[-1], "year")

        # Split the numbers input and check that it is valid
        numbers = check_and_get_ranges(args.numbers, MAX_NUMBERS[0], MAX_NUMBERS[-1], "year")

        results = {}
        for court in tqdm(courts, desc="Court", ncols=80):
            for year in tqdm(years, desc="Year", ncols=80, leave=False):
                for num in tqdm(numbers, desc="Num", ncols=80, leave=False):
                    target = f"{court}-{num}/{year}"
                    page = get_bvger_search(
                        target,
                        lang=query_lang,
                        verbose=verbose,
                    )
                    if page:
                        temp = get_bvger_page(
                            page,
                            lang=query_lang,
                            full_text=full_text,
                            download=download,
                            download_folder=download_folder,
                            verbose=verbose,
                        )
                        if temp:
                            results[temp["id"]] = temp

        df = pd.DataFrame.from_dict(results, orient="index")
        df.to_excel(os.path.join(download_folder, f"bvger_results_{datetime.datetime.now().strftime('%y-%m-%dT%H-%M-%S')}.xlsx"))
    else:
        parser.print_help(sys.stderr)
        exit(-1)
