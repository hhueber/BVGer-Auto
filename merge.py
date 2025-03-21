import os
import pandas as pd

path = os.path.join("download", "all")

all_excel_files = [os.path.join(path, file) for file in os.listdir(path) if file[-4:] == "xlsx"]

# Concat
df = pd.concat([pd.read_excel(excel_file) for excel_file in all_excel_files], ignore_index=True)

# Drop Unnamed
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Create sorting column
df[["court", "number_year"]] = df["title"].str.split("-", n=1, expand=True)
df[["number", "year"]] = df["number_year"].str.split("/", n=1, expand=True)
del df["number_year"]

# Set index
df.set_index("id")

# Reorder columns
df = df[[
    "id",
    "link_page",
    "query_lang",
    "court",
    "number",
    "year",
    "title",
    "full_text",
    "file_text",
    "link_pdf",
    "file_pdf",
    "COUR",
    "DATE DE LA DÉCISION",
    "LANGUE",
    "ATAF / AUTRES ARRÊTS",
    "ATAF CITÉS",
    "AUTRES ARRÊTS DU TAF CITÉS",
    "MOTS-CLÉS RECONNUS",
    "ANNÉE DE RÉCEPTION",
    "DATE DE LA PUBLICATION",
    "LÉGISLATION FÉDERALE",
    "RECUEIL SYSTÉMATIQUE",
    "RECUEIL OFFICIEL DU DROIT FÉDÉRAL",
    "ATF CITÉS",
    "AUTRES ARRÊTS DU TF CITÉS",
    "FEUILLE FÉDÉRALE",
    "AUTRES ARRÊTS DU TPF CITÉS",
    "DÉCISION ATAF LIÉE",
    "BULLETIN OFFICIEL",
    "ARRÊTS DU RECUEIL OFFICIEL TPF CITÉS",
]]

# Save
df.to_excel(os.path.join(path, "..", "all.xlsx"))

print(df.head())
