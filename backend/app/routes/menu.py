from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.menu import Category, MenuItem

router = APIRouter()


def item_response(i: MenuItem) -> dict:
    tag_list = [t.strip() for t in (i.tags or "").split(",") if t.strip()]
    return {
        "id": i.id,
        "category_id": i.category_id,
        "name": i.name,
        "description": i.description,
        "price_cents": i.price_cents,
        "image_url": i.image_url,
        "tags": tag_list,
        "popular": i.popular or False,
        "sort_order": i.sort_order,
    }


@router.get("/api/menu/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    categories = result.scalars().all()
    return [
        {"id": c.id, "name": c.name, "slug": c.slug, "image_url": c.image_url, "sort_order": c.sort_order}
        for c in categories
    ]


@router.get("/api/menu/items")
async def list_menu_items(
    category_id: str | None = Query(None),
    category_slug: str | None = Query(None),
    tag: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(MenuItem).where(MenuItem.is_available == True)

    if category_id:
        query = query.where(MenuItem.category_id == category_id)
    elif category_slug:
        cat_result = await db.execute(select(Category).where(Category.slug == category_slug))
        category = cat_result.scalar_one_or_none()
        if not category:
            return []
        query = query.where(MenuItem.category_id == category.id)

    if tag:
        query = query.where(MenuItem.tags.ilike(f"%{tag}%"))

    query = query.order_by(MenuItem.sort_order)
    result = await db.execute(query)
    return [item_response(i) for i in result.scalars().all()]


@router.get("/api/menu/items/{item_id}")
async def get_menu_item(item_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        return {"error": "Not found"}
    return item_response(item)


@router.get("/api/menu/full")
async def full_menu(
    tag: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    cat_result = await db.execute(select(Category).order_by(Category.sort_order))
    categories = cat_result.scalars().all()

    menu = []
    for cat in categories:
        item_query = select(MenuItem).where(
            MenuItem.category_id == cat.id, MenuItem.is_available == True
        ).order_by(MenuItem.sort_order)
        if tag:
            item_query = item_query.where(MenuItem.tags.ilike(f"%{tag}%"))
        item_result = await db.execute(item_query)
        items = [item_response(i) for i in item_result.scalars().all()]
        if not items and tag:
            continue
        menu.append({
            "id": cat.id, "name": cat.name, "slug": cat.slug, "image_url": cat.image_url, "items": items,
        })
    return menu


@router.get("/api/menu/tags")
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MenuItem.tags).where(MenuItem.tags.isnot(None), MenuItem.tags != ""))
    tags_set = set()
    for row in result.all():
        if row[0]:
            for t in row[0].split(","):
                tag = t.strip()
                if tag:
                    tags_set.add(tag)
    return sorted(tags_set)
