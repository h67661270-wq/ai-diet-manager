import csv
import math
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


DATA_DIR = Path(__file__).with_name("data")
NUTRIENT_FIELDS = ("energy_kcal", "protein_g", "fat_g", "carbs_g")
NutritionBasis = Literal["per_100g", "per_serving"]


def nonnegative_number(value: object) -> float | None:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


class Nutrients(BaseModel):
    energy_kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None

    @field_validator(*NUTRIENT_FIELDS, mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> float | None:
        return nonnegative_number(value)


class RecognizedFood(Nutrients):
    name: str = Field(min_length=1, max_length=50)
    category: str = "其他"
    portion: str = Field(default="", max_length=60)
    reference_query: str | None = Field(default=None, max_length=70)
    english_name: str | None = Field(default=None, max_length=120)
    estimated_grams: float | None = None
    uncertain: bool = False

    @field_validator("name", "category", "portion", "reference_query", "english_name", mode="before")
    @classmethod
    def clean_text(cls, value: object, info):
        text = value.strip() if isinstance(value, str) else ""
        limits = {"name": 50, "category": 40, "portion": 60, "reference_query": 70, "english_name": 120}
        if text:
            return text[:limits[info.field_name]]
        return {"name": "", "category": "其他", "portion": ""}.get(info.field_name)

    @field_validator("estimated_grams", mode="before")
    @classmethod
    def parse_weight(cls, value: object) -> float | None:
        return nonnegative_number(value) or None

    @field_validator("uncertain", mode="before")
    @classmethod
    def parse_uncertainty(cls, value: object) -> bool:
        return value in (True, "true", "True")


class PhotoRecognition(BaseModel):
    foods: list[RecognizedFood] = Field(default_factory=list)
    notes: str = ""
    totals: Nutrients = Field(default_factory=Nutrients)

    @field_validator("foods", mode="before")
    @classmethod
    def keep_recognizable_foods(cls, value: object) -> list[RecognizedFood]:
        foods = []
        if isinstance(value, list):
            for item in value:
                try:
                    foods.append(RecognizedFood.model_validate({"name": item} if isinstance(item, str) else item))
                except ValidationError:
                    continue
        return foods

    @field_validator("notes", mode="before")
    @classmethod
    def parse_notes(cls, value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    @field_validator("totals", mode="before")
    @classmethod
    def parse_totals(cls, value: object) -> object:
        return value if isinstance(value, dict) else {}


class ReferenceChoice(Nutrients):
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
    status: Literal["estimated", "unestimated", "needs_confirmation"]


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


def estimate_food(
    food: RecognizedFood,
    reference: FoodReference | None,
    adjustment: ReferenceChoice | None,
) -> FoodEstimate:
    values = {key: getattr(food, key) for key in NUTRIENT_FIELDS}
    if reference and adjustment:
        values.update(adjustment.model_dump(include=set(NUTRIENT_FIELDS), exclude_none=True))
    if food.uncertain:
        status = "needs_confirmation"
    else:
        status = "estimated" if any(value is not None for value in values.values()) else "unestimated"
    return FoodEstimate(
        name=food.name,
        category=food.category,
        portion=food.portion,
        estimated_grams=food.estimated_grams,
        reference=reference.citation() if reference else None,
        status=status,
        **{key: round(value, 1) for key, value in values.items() if value is not None},
    )


def meal_totals(foods: list[FoodEstimate], overall_estimate: Nutrients) -> Nutrients:
    totals = {}
    for key in NUTRIENT_FIELDS:
        values = [getattr(food, key) for food in foods]
        if values and all(value is not None for value in values):
            totals[key] = round(sum(values), 1)
        elif values:
            totals[key] = getattr(overall_estimate, key)
    return Nutrients(**totals)
