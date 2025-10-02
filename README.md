# BVGer Auto

Scrapping of the Swiss Federal Administrative Court jurisprudence database.

## Setup

1. Clone the repo, cd into it.
    - `git clone git@github.com:hhueber/BVGer-Auto.git; cd BVGer-Auto`
2. Create virtual environment.
    - `python -m venv env; source env/bin/activate`
3. Install requirements.
    - `pip install -Ur requirements.txt`
4. Install pre-commit.
    - `pre-commit install`
5. Configure the instance.
    - `cp secret.dist.py secret.py`

## Usage

### Récupérer un ou des ATF : `bvger_auto.py`

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

#### Récupérer un ATF : `page`

```
$ python bvger_auto.py page --help

usage: BVGer Auto page [-h] title

positional arguments:
  title       Specific page title ("D-1234/2020")

options:
  -h, --help  show this help message and exit
```

Par exemple, pour récupérer les informations sur l'ATF "D-1234/2020", et sauvegarder le texte correspondant au format PDF :

```bash
python bvger_auto.py -d page D-1234/2020
```

#### Récupérer plusieurs ATF : `collect`

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

Par exemple, pour récupérer les 20 premiers ATF numérotés (s'ils existent) de la Cour V (droit d'asile), de l'année 2025 :

```bash
python bvger_auto.py -d collect E 2025 1-20
```

Cette commande spécifique va télécharger les trois ATF numérotés entre 1 et 20 qui existent en 2025 pour cette cour spécifique, à savoir E-11/2025, E-15/2025 et E-18/2025.

### `merge.py`

_TODO_

### `pattern_counter.py`

_TODO_