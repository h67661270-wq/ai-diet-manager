"""Build the local Chinese food and recipe references from the cited source files."""

import argparse
import csv
import math
import re
from collections import defaultdict
from io import TextIOWrapper
from pathlib import Path
from zipfile import ZipFile

from opencc import OpenCC
from openpyxl import load_workbook


DATA_DIR = Path(__file__).resolve().parent
NUTRIENTS = ("energy_kcal", "protein_g", "fat_g", "carbs_g")
HEADER = ("id", "name", "aliases", "source_name", *NUTRIENTS)
TFDA_FIELDS = dict(zip(("熱量", "粗蛋白", "粗脂肪", "總碳水化合物"), NUTRIENTS))
UNITS = dict(zip(NUTRIENTS, ("kcal", "g", "g", "g")))
SIMPLIFIED = OpenCC("t2s")
TRADITIONAL = OpenCC("s2t")
TFDA_ALIASES = {
    "白馒头": ("馒头", "熟馒头"),
    "熟水饺(高丽菜水饺)": ("熟包菜水饺", "熟卷心菜水饺", "熟高丽菜水饺"),
}
RECIPE_ALIASES = {
    "mapo tofu": "麻婆豆腐",
    "kung pao chicken": "宫保鸡丁",
    "twice-cooked pork": "回锅肉",
    "salted fish and chicken tofu pot": "咸鱼鸡粒豆腐煲",
    "white cut chicken": "白切鸡",
    "steamed sea bass": "清蒸鲈鱼",
}


def aliases(name, terms):
    variants = dict.fromkeys(
        variant.strip()
        for term in (name, *terms)
        for variant in (term, SIMPLIFIED.convert(term), TRADITIONAL.convert(term))
    )
    return "|".join(variant for variant in variants if variant and variant != name)


def as_number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def tfda_rows(archive_path):
    with ZipFile(archive_path) as archive:
        member, = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        with archive.open(member) as csv_file:
            records = {}
            values = defaultdict(dict)
            for row in csv.DictReader(TextIOWrapper(csv_file, encoding="utf-8-sig")):
                identifier = row["整合編號"].strip()
                field = TFDA_FIELDS.get(row["分析項"])
                if not identifier or not field or row["含量單位"] != UNITS[field]:
                    continue
                value = as_number(row["每100克含量"])
                if value is None:
                    continue
                records.setdefault(identifier, row)
                values[identifier][field] = value
    for identifier, nutrients in values.items():
        if len(nutrients) != len(NUTRIENTS):
            continue
        row = records[identifier]
        original = row["樣品名稱"].strip()
        name = SIMPLIFIED.convert(original)
        extra = re.split(r"[、；;,，|]", f'{row["俗名"]};{row["樣品英文名稱"]}')
        terms = [original, *extra, *TFDA_ALIASES.get(name, ())]
        yield identifier, name, aliases(name, terms), original, *(nutrients[key] for key in NUTRIENTS)


def worksheet_rows(path, sheet):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = workbook[sheet].values
        header = next(rows)
        for number, row in enumerate(rows, start=2):
            yield number, dict(zip(header, row))
    finally:
        workbook.close()


def recipe_values(row, columns, servings=1):
    values = [as_number(row[key]) for key in columns]
    if not servings or any(value is None for value in values):
        return None
    energy, protein, fat, _ = values
    # Omit clearly inconsistent rows, allowing for composition and rounding differences.
    if energy + 10 * servings < 0.65 * (4 * protein + 9 * fat):
        return None
    return tuple(round(value / servings, 2) for value in values)


def six_cuisines_rows(path):
    columns = ("Energy_per_serving", "Protein_per_serving", "Fat_per_serving", "CHO_per_serving")
    for number, row in worksheet_rows(path, "Results per serving"):
        name = SIMPLIFIED.convert(row["菜名"].strip())
        english = (row["Dish_name"] or "").strip()
        nutrients = recipe_values(row, columns)
        if nutrients is not None:
            terms = (english, RECIPE_ALIASES.get(english.casefold(), ""))
            yield number, name, aliases(name, terms), f'{row["菜系"]} · {english}', *nutrients


def sichuan_cantonese_rows(path, prefix, cuisine):
    columns = ("Energy (kcal)", "Protein (g)", "Fat (g)", "Carbohydrate (g)")
    for _, row in worksheet_rows(path, "Sheet1"):
        english = row["Dish name"].strip()
        nutrients = recipe_values(row, columns, as_number(row["Serving"]))
        if nutrients is not None:
            name = RECIPE_ALIASES.get(english.casefold()) or english
            yield f'{prefix}-{row["No."]}', name, aliases(name, (english,)), f"{cuisine} · {english}", *nutrients


def write_csv(filename, rows):
    with (DATA_DIR / filename).open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(HEADER)
        count = 0
        for row in rows:
            writer.writerow(row)
            count += 1
    print(f"{filename}: {count} records")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("tfda", "six-cuisines", "sichuan", "cantonese"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    args = parser.parse_args()
    write_csv("tfda_foods.csv", tfda_rows(args.tfda))
    write_csv("chinese_recipes.csv", six_cuisines_rows(args.six_cuisines))
    write_csv("sichuan_cantonese_recipes.csv", (
        row for path, prefix, cuisine in ((args.sichuan, "sc", "川菜"), (args.cantonese, "gd", "粤菜"))
        for row in sichuan_cantonese_rows(path, prefix, cuisine)
    ))


if __name__ == "__main__":
    main()
