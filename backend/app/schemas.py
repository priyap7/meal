from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class NutritionItem(BaseModel):
    food_name: str = Field(min_length=1, max_length=120)
    portion_g: float = Field(gt=0, le=3000)
    ingredients_observed: list[str] = []
    ingredients_likely: list[str] = []
    calories: float = Field(ge=0, le=10000)
    protein_g: float = Field(ge=0, le=1000)
    carbs_g: float = Field(ge=0, le=1000)
    fat_g: float = Field(ge=0, le=1000)
    fibre_g: float = Field(ge=0, le=1000)
    confidence: float = Field(ge=0, le=1)
    calorie_range: list[float] = Field(min_length=2, max_length=2)
    data_source: str = "AI estimate; not database verified"
    assumptions: list[str] = []

class AnalysisResult(BaseModel):
    items: list[NutritionItem]
    questions: list[str] = []
    overall_notes: list[str] = []

class MealCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    meal_type: str = Field(default="snack", pattern="^(breakfast|lunch|dinner|snack)$")
    eaten_at: datetime | None = None
    items: list[dict] = []
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    fibre_g: float = Field(ge=0)
    notes: str = ""
    source: str = "manual"

class MealOut(MealCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

class GoalsIn(BaseModel):
    calories: float = Field(gt=0, le=10000)
    protein_g: float = Field(gt=0, le=1000)
    carbs_g: float = Field(gt=0, le=1500)
    fat_g: float = Field(gt=0, le=500)
    fibre_g: float = Field(gt=0, le=200)
