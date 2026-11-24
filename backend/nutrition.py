import csv
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


DATA_PATH = Path(__file__).with_name("data") / "usda_sr_legacy.csv"
NUTRIENT_FIELDS = ("energy_kcal", "protein_g", "fat_g", "carbs_g")


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
    estimated_grams: float | None = Field(default=None, gt=0, le=2000)
    uncertain: bool = True


class PhotoRecognition(BaseModel):
    foods: list[RecognizedFood] = Field(max_length=12)
    notes: str = Field(default="", max_length=240)


class ReferenceChoice(BaseModel):
    food_index: int = Field(ge=0)
    fdc_id: int


class ReferenceReview(BaseModel):
    matches: list[ReferenceChoice] = Field(max_length=12)
    question: str = Field(default="", max_length=160)


class NutritionSource(BaseModel):
    name: str
    fdc_id: int
    url: str


class FoodEstimate(Nutrients):
    name: str
    category: str
    portion: str
    estimated_grams: float | None
    reference: NutritionSource | None
    status: Literal["estimated", "missing_reference", "missing_portion", "needs_confirmation"]


class MealAnalysis(BaseModel):
    foods: list[FoodEstimate]
    notes: str
    totals: Nutrients
    follow_up: str = ""


@dataclass(frozen=True)
class FoodReference:
    fdc_id: int
    name: str
    source_name: str
    per_100g: dict[str, float]

    def citation(self) -> NutritionSource:
        return NutritionSource(
            name=self.name,
            fdc_id=self.fdc_id,
            url=f"https://fdc.nal.usda.gov/food-details/{self.fdc_id}/nutrients",
        )


def normalize_term(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKC", value).casefold() if char.isalnum()
    )


@lru_cache(maxsize=1)
def reference_index() -> dict[str, tuple[FoodReference, ...]]:
    index: dict[str, list[FoodReference]] = {}
    with DATA_PATH.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            reference = FoodReference(
                fdc_id=int(row["fdc_id"]),
                name=row["name"],
                source_name=row["source_name"],
                per_100g={key: float(row[key]) for key in NUTRIENT_FIELDS},
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
    labels = (food.name,) if food.category == "复合菜" else (food.reference_query, food.name)
    for label in labels:
        if label:
            for entry in index.get(normalize_term(label), ()):
                references[entry.fdc_id] = entry
    return list(references.values())[:3]


def estimate_food(food: RecognizedFood, reference: FoodReference | None) -> FoodEstimate:
    grams = None if food.uncertain else food.estimated_grams
    values = {}
    if food.uncertain:
        status = "needs_confirmation"
    elif reference is None:
        status = "missing_reference"
    elif grams is None:
        status = "missing_portion"
    else:
        status = "estimated"
        values = {key: value * grams / 100 for key, value in reference.per_100g.items()}
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
