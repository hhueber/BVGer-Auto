from tqdm import tqdm
import json
from pprint import pprint
import os.path
from collections import Counter, defaultdict
import re

import pandas as pd
from nltk import word_tokenize

TEST_FILE_2 = os.path.join("download", "2019", "txt", "E-4930-2019.txt")  # LGBT etc.
TEST_LANG = "fr"
PATTERNS_FILES = {
    "de": os.path.join("patterns", "patterns_de"),
    "fr": os.path.join("patterns", "patterns_fr"),
    "it": os.path.join("patterns", "patterns_it"),
    "*": os.path.join("patterns", "patterns_more"),
}
PATTERNS = {}

def gen_pattern_for_regex(lang):
    patterns = set()
    raw = open(PATTERNS_FILES[lang], "r").readlines() + open(PATTERNS_FILES["*"], "r").readlines()

    for keyword in raw:
        if "#" not in keyword:
            pat = keyword.strip().lower()
            if not (pat.startswith("\"") and pat.endswith("\"")):
                pat = f"\"{pat}\""
            pat = pat.replace("*", ".*")
            pat = f"^{pat[1:-1]}$"
            patterns.add(re.compile(rf"{pat}"))

    return patterns

for lang in PATTERNS_FILES:
    PATTERNS[lang] = gen_pattern_for_regex(lang)

def extract_patterns_and_words(file_path):
    with open(file_path, "r") as f:
        raw = f.read()

    tokens = word_tokenize(raw)
    words = [w.lower() for w in tokens]
    count = Counter(words)

    res_pattern_words = defaultdict(lambda: {"words": dict(), "total": 0})
    res_word_patterns = defaultdict(lambda: {"patterns": list(), "total": 0})

    for regex_pattern in PATTERNS["fr"]:
        for word in count.keys():
            if re.search(regex_pattern, word):
                res_pattern = regex_pattern.pattern
                res_word = word
                res_count = count.get(word)

                res_pattern_words[res_pattern]["words"].update({res_word: count.get(res_word)})
                res_pattern_words[res_pattern]["total"] += count.get(res_word)

                res_word_patterns[res_word]["patterns"].append(res_pattern)
                res_word_patterns[res_word]["total"] += 1

    return {"patterns": res_pattern_words, "words": res_word_patterns}

def format_for_df(file):
    res = extract_patterns_and_words(file)

    patterns = ", ".join([f"{key}: {value['total']}" for key, value in res["patterns"].items()])
    patterns_total = sum(value["total"] for value in res["patterns"].values())

    words = ", ".join([f"{key}: {value['total']}" for key, value in res["words"].items()])
    words_total = sum(value["total"] for value in res["words"].values())

    return patterns, len(res["patterns"]), patterns_total, words, len(res["words"]), words_total

if __name__ == "__main__":
    print("start main")
    tqdm.pandas()

    print("reading file")
    df = pd.read_excel(os.path.join("download", "all.xlsx"))

    print("applying")
    df[["patterns", "num_patterns", "patterns_total", "words", "num_words", "words_total"]] = df.progress_apply(
        lambda row: format_for_df(os.path.join("download", str(row["year"]), "txt", row["file_text"])),
        axis=1,
        result_type='expand',
    )

    print("saving")
    df.to_excel(os.path.join("download", "all_with_stats.xlsx"))

    print(df.head())
