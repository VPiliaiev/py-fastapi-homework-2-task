import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import Request
from sqlalchemy import desc

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas import MovieListResponseSchema, MovieListItemSchema, MovieDetailSchema
from schemas.movies import MovieCreateSchema, MovieUpdateSchema

router = APIRouter(
    prefix="/movies",
    tags=["Movies"]
)


@router.get("/", response_model=MovieListResponseSchema)
async def read_movies(
        request: Request,
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=20)
):
    count_stmt = select(func.count()).select_from(MovieModel)
    total_items = (await db.execute(count_stmt)).scalar_one()
    if total_items == 0:
        raise HTTPException(404, "No movies found.")
    total_pages = math.ceil(total_items / per_page)
    if page > total_pages:
        raise HTTPException(404, "No movies found.")
    offset = (page - 1) * per_page
    stmt = select(MovieModel).order_by(desc(MovieModel.id)).limit(per_page).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()
    base_url = "/theater/movies/"
    prev_page = f"{base_url}?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = f"{base_url}?page={page + 1}&per_page={per_page}" if page < total_pages else None
    movies = [
        MovieListItemSchema.model_validate(movie, from_attributes=True)
        for movie in items
    ]
    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.post("/", status_code=201, response_model=MovieDetailSchema)
async def create_movie(movie: MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    movie_stmt = select(MovieModel).where(
        MovieModel.name == movie.name,
        MovieModel.date == movie.date
    )
    movie_result = await db.execute(movie_stmt)
    if movie_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists."
        )

    country_stmt = select(CountryModel).where(CountryModel.code == movie.country)
    country_result = await db.execute(country_stmt)
    existing_country = country_result.scalar_one_or_none()
    if not existing_country:
        existing_country = CountryModel(code=movie.country, name=None)
        db.add(existing_country)
        await db.flush()

    async def get_or_create_entities(model, names):
        entities = []
        for name in names:
            res = await db.execute(select(model).where(model.name == name))
            obj = res.scalar_one_or_none()
            if not obj:
                obj = model(name=name)
                db.add(obj)
                await db.flush()
            entities.append(obj)
        return entities

    genres = await get_or_create_entities(GenreModel, movie.genres)
    actors = await get_or_create_entities(ActorModel, movie.actors)
    languages = await get_or_create_entities(LanguageModel, movie.languages)

    new_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country=existing_country,
        genres=genres,
        actors=actors,
        languages=languages
    )

    try:
        db.add(new_movie)
        await db.commit()

        stmt = (
            select(MovieModel)
            .options(
                selectinload(MovieModel.country),
                selectinload(MovieModel.genres),
                selectinload(MovieModel.actors),
                selectinload(MovieModel.languages)
            )
            .where(MovieModel.id == new_movie.id)
        )
        final_res = await db.execute(stmt)
        return final_res.scalar_one()

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.get("/{movie_id}/", response_model=MovieDetailSchema)
async def read_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages)
        )
        .where(MovieModel.id == movie_id)
    )

    result = await db.execute(stmt)
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return movie


@router.delete("/{movie_id}/", status_code=204)
async def remove_film(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    db_movie = result.scalar_one_or_none()
    if not db_movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )
    await db.delete(db_movie)
    await db.commit()
    return None


@router.patch("/{movie_id}/", status_code=200)
async def update_movie(
        movie_id: int,
        movie_update: MovieUpdateSchema,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    try:
        update_data = movie_update.model_dump(exclude_unset=True)

        if not update_data:
            pass

        for key, value in update_data.items():
            setattr(movie, key, value)

        await db.commit()

        return {"detail": "Movie updated successfully."}

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
