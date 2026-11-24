import csv
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


DATA_DIR = Path(__file__).with_name("data")
NUTRIENT_FIELDS = ("energy_kcal", "protein_g", "fat_g", "carbs_g")
NutritionBasis = Literal["per_100g", "per_serving"]


class Nutrients(BaseModel):
    energy_kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None


class RecognizedFood(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=40)
    portion: str = Field(default="", max_length=60)
    reference_query: str | None = Field(default=None, max_length=70)
    english_name: str | None = Field(default=None, max_length=120)
    estimated_grams: float | None = Field(default=None, gt=0, le=2000)
    uncertain: bool = True


class PhotoRecognition(BaseModel):
    foods: list[RecognizedFood] = Field(max_length=12)
    notes: str = Field(default="", max_length=240)


class ReferenceChoice(BaseModel):
    food_index: int = Field(ge=0)
    reference_id: str


class ReferenceReview(BaseModel):
    matches: list[ReferenceChoice] = Field(max_length=12)
    question: str = Field(default="", max_length=160)


class NutritionSource(BaseModel):
    id: str
    name: str
    label: str
    url: str
    basis: NutritionBasis
    nutrients: Nutrients
    fdc_id: int | None = None


class FoodEstimate(Nutrients):
    name: str
    category: str
    portion: str
    estimated_grams: float | None
    reference: NutritionSource | None
    status: Literal["estimated", "missing_reference", "missing_portion", "needs_confirmation", "recipe_reference"]


class MealAnalysis(BaseModel):
    foods: list[FoodEstimate]
    notes: str
    totals: Nutrients
    follow_up: str = ""


@dataclass(frozen=True)
class ReferenceDataset:
    key: str
    filename: str
    label: str
    url: str
    basis: NutritionBasis
    id_column: str = "id"


DATASETS = (
    ReferenceDataset("tfda", "tfda_foods.csv", "食药署食品营养成分资料", "https://data.gov.tw/dataset/8543", "per_100g"),
    ReferenceDataset("usda", "usda_sr_legacy.csv", "USDA", "https://fdc.nal.usda.gov/food-details/{id}/nutrients", "per_100g", "fdc_id"),
    ReferenceDataset("chinese", "chinese_recipes.csv", "六大菜系参考配方", "https://doi.org/10.6084/m9.figshare.29977027.v2", "per_serving"),
    ReferenceDataset("sc_gd", "sichuan_cantonese_recipes.csv", "川菜和粤菜参考配方", "https://doi.org/10.6084/m9.figshare.28457018.v4", "per_serving"),
)


@dataclass(frozen=True)
class FoodReference:
    source_id: str
    name: str
    source_name: str
    nutrients: dict[str, float]
    dataset: ReferenceDataset

    @property
    def id(self) -> str:
        return f"{self.dataset.key}:{self.source_id}"

    def citation(self) -> NutritionSource:
        return NutritionSource(
            id=self.id,
            name=self.name,
            label=self.dataset.label,
            url=self.dataset.url.format(id=self.source_id),
            basis=self.dataset.basis,
            nutrients=Nutrients(**self.nutrients),
            fdc_id=int(self.source_id) if self.dataset.key == "usda" else None,
        )


def normalize_term(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKC", value).casefold() if char.isalnum()
    )


@lru_cache(maxsize=1)
def reference_index() -> dict[str, tuple[FoodReference, ...]]:
    index: dict[str, list[FoodReference]] = {}
    for dataset in DATASETS:
        with (DATA_DIR / dataset.filename).open(encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                reference = FoodReference(
                    source_id=row[dataset.id_column],
                    name=row["name"],
                    source_name=row["source_name"],
                    nutrients={key: float(row[key]) for key in NUTRIENT_FIELDS},
                    dataset=dataset,
                )
                terms = {normalize_term(value) for value in [row["name"], *row["aliases"].split("|")]}
                for term in terms - {""}:
                    index.setdefault(term, []).append(reference)
    return {term: tuple(entries) for term, entries in index.items()}


def retrieve_references(food: RecognizedFood) -> list[FoodReference]:
    if food.uncertain:
        return []
    index = reference_index()
    references = {}
    labels = (food.name, food.english_name)
    if food.category != "复合菜":
        labels = (food.reference_query, *labels)
    for label in labels:
        if label:
            for entry in index.get(normalize_term(label), ()):
                references[entry.id] = entry
    entries = sorted(references.values(), key=lambda entry: entry.dataset.basis != "per_100g")
    return entries[:5]


def estimate_food(food: RecognizedFood, reference: FoodReference | None) -> FoodEstimate:
    grams = None if food.uncertain else food.estimated_grams
    values = {}
    if food.uncertain:
        status = "needs_confirmation"
    elif reference is None:
        status = "missing_reference"
    elif reference.dataset.basis == "per_serving":
        status = "recipe_reference"
    elif grams is None:
        status = "missing_portion"
    else:
        status = "estimated"
        values = {key: value * grams / 100 for key, value in reference.nutrients.items()}
    return FoodEstimate(
        name=food.name,
        category=food.category,
        portion=food.portion,
        estimated_grams=grams,
        reference=reference.citation() if reference else None,
        status=status,
        **{key: round(value, 1) for key, value in values.items()},
    )


def meal_totals(foods: list[FoodEstimate]) -> Nutrients:
    totals = {}
    for key in NUTRIENT_FIELDS:
        values = [getattr(food, key) for food in foods]
        totals[key] = round(sum(values), 1) if values and all(value is not None for value in values) else None
    return Nutrients(**totals)
