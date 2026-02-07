from datetime import date, timedelta
from typing import Optional, Literal, List
from pydantic import BaseModel, ConfigDict, field_validator, Field


class CountrySchema(BaseModel):
    id: int
    code: str
    name: str | None


class GenreSchema(BaseModel):
    id: int
    name: str


class ActorSchema(BaseModel):
    id: int
    name: str


class LanguageSchema(BaseModel):
    id: int
    name: str


class MovieBase(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str
    model_config = ConfigDict(from_attributes=True)


class MovieListItemSchema(MovieBase):
    pass


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int
    model_config = ConfigDict(from_attributes=True)


class MovieDetailSchema(MovieBase):
    status: str
    budget: float
    revenue: float
    country: CountrySchema
    genres: list[GenreSchema]
    actors: list[ActorSchema]
    languages: list[LanguageSchema]
    model_config = ConfigDict(from_attributes=True)


class MovieCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: Literal["Released", "Post Production", "In Production"]
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str = Field(..., min_length=2, max_length=3)
    genres: List[str]
    actors: List[str]
    languages: List[str]

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: date) -> date:
        one_year_from_now = date.today() + timedelta(days=365)
        if v > one_year_from_now:
            raise ValueError("Date cannot be more than one year in the future")
        return v


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[Literal["Released", "Post Production", "In Production"]] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)

    model_config = ConfigDict(from_attributes=True)
