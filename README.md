# BVGer Auto

Scrapping of the Swiss Federal Administrative Court jurisprudence database.

## Setup

1. Clone the repo, cd into it.
    - `git clone XXX; cd XXX`
2. Create virtual environment.
    - `python -m venv env; source env/bin/activate`
3. Install requirements.
    - `pip install -Ur requirements.txt`
4. Install pre-commit.
    - `pre-commit install`
5. Configure the instance.
    - `cp secret.dist.py secret.py`

## Usage

### `bvger_auto.py`

Ce script va parcourir le site https://bvger.weblaw.ch pour récupérer soit une liste d'ATF, soit un ATF précis.

```
$ python bvger_auto.py --help

usage: BVGer Auto [-h] [-l QUERY_LANG] [-v] [-f] [-d] [-o DOWNLOAD_FOLDER] {page,collect} ...

Crawler for BVGer

positional arguments:
  {page,collect}        `page` for a specific page, `collect` for multiple pages
    page                Search and return a specific page
    collect             Search and return multiple pages

options:
  -h, --help            show this help message and exit
  -l QUERY_LANG, --query-lang QUERY_LANG
                        Lang for the research interface
  -v, --verbose         Debug
  -f, --full-text       Save the full text in the resulting dictionary. If `download` is True, the text is saved as a file instead
  -d, --download        Download the PDF. If `full_text` is True, the text is saved as a file as well
  -o DOWNLOAD_FOLDER, --download-folder DOWNLOAD_FOLDER
                        Where the result will be saved

Remember, be excellent to each others
```

```
$ python bvger_auto.py page --help

usage: BVGer Auto page [-h] title

positional arguments:
  title       Specific page title ("D-1234/2020")

options:
  -h, --help  show this help message and exit
```

```
$ python bvger_auto.py collect --help

usage: BVGer Auto collect [-h] courts years numbers

positional arguments:
  courts      Courts to be used for collection, either a single letter (A), or multiple letters ("A;F")
  years       Years to be used for collection, either a single year (2007), or multiple years ("2007;2025"), or a range ("2007-2025")
  numbers     Numbers to be used for collection, either a single number (1), or multiple numbers ("1;9999"), or a range ("1-9999")

options:
  -h, --help  show this help message and exit
```

### `merge.py`

_TODO_

### `pattern_counter.py`

_TODO_