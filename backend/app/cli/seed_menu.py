"""Seed the database with the full HongShing dinner menu."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session, Base, engine as db_engine
from app.models.menu import Category, MenuItem

settings = get_settings()

CLOUD_ASSET_BASE = "https://cloud-assets.orderingplus.com/image/upload/f_auto,q_auto,h_600,c_limit/hongshing"

CLOUD_ASSET_BASE = "https://cloud-assets.orderingplus.com/image/upload/f_auto,q_auto,h_600,c_limit/hongshing"

CATEGORIES = [
    {"name": "Iconic Dishes", "slug": "iconic", "sort_order": 0},
    {"name": "Appetizers", "slug": "appetizers", "sort_order": 1},
    {"name": "Soups", "slug": "soups", "sort_order": 2},
    {"name": "Dim Sum", "slug": "dim-sum", "sort_order": 3},
    {"name": "From Sea to Table", "slug": "seafood", "sort_order": 4},
    {"name": "Chicken", "slug": "chicken", "sort_order": 5},
    {"name": "Beef", "slug": "beef", "sort_order": 6},
    {"name": "Duck", "slug": "duck", "sort_order": 7},
    {"name": "Vegetables", "slug": "vegetables", "sort_order": 8},
    {"name": "Rice", "slug": "rice", "sort_order": 9},
    {"name": "Noodles", "slug": "noodles", "sort_order": 10},
]

PRODUCTS_BY_CATEGORY = {
    "iconic": [
        ("General Tao Chicken", "House General Tao Sauce, Hoisin, House Sambal", 2000, "gfp0ooz5kqitynqolekb/1616624100.jpg", ["Iconic", "Chicken", "Spicy", "Halal"], True),
        ("Chili Chicken", "Bird's Eye Chili, Garlic, Soy Sauce", 2000, "qoms53lwuhb4nmdmm26q/1616624244.jpg", ["Iconic", "Chicken", "Spicy", "Halal"], True),
        ("Ma La Wings", "8 pcs, Szechuan Peppercorn, Black Cardamom, Cumin", 1900, "wsoyutsc08jhisps8r60/1616623380.jpg", ["Iconic", "Chicken", "Spicy", "Halal"], True),
        ("Spicy Shrimps", "Jumbo Shrimp, House Sambal, Bell Pepper", 1800, "xvf6ry67dgussmkhtcbx/1599685187.jpg", ["Iconic", "Seafood", "Spicy"], True),
        ("Garlic Beef Tenderloin", "Garlic, Soy Sauce, Butter", 2500, "gwmenbptdwsqb330ik17/1664085547.jpg", ["Iconic", "Beef", "Halal"], True),
        ("Crispy Beef", "Golden Fried Beef Strips, Sweet Soy Glaze", 2200, "eiitevflt0zd5ehetqey/1616623989.jpg", ["Iconic", "Beef", "Spicy", "Halal"], True),
    ],
    "appetizers": [
        ("Vegetable Spring Roll", "Per roll, Cabbage, Carrots, Mixed Vegetables", 300, "jhgiofk0di7f32yjzwws/1640965996.jpg", ["Vegetarian"], False),
        ("Shrimp Rolls", "3 pcs, Golden Fried Rice Wrapper, Minced Shrimp", 600, "p5gofpyj9fg6dyds5e6l/1616623325.jpg", ["Seafood"], False),
        ("Fried Shrimp Wontons", "6 pcs, Shrimp, Wood Ear Mushrooms, Sweet Sour Sauce", 1400, "axtamzz4spr1hzpkfxp4/1640965598.jpg", ["Seafood"], False),
        ("Fried Chicken Balls", "6 pcs, Golden Fried Batter Wrapped Chicken Breast", 1500, "tonmzyu53xgpvhajicvj/1616623212.jpg", ["Chicken", "Halal"], False),
        ("Classic Wings", "8 pcs, Black Pepper, Lemon", 1800, "tvyu8ygw5hrmc0kyfnzu/1616623255.jpg", ["Chicken", "Halal"], False),
        ("Spicy Dry Wings", "8 pcs, House Sambal, Bell Pepper", 1900, "rztvolqu13keh814lhmb/1616623355.jpg", ["Chicken", "Spicy", "Halal"], False),
        ("Honey Garlic Wings", "8 pcs, Garlic, Soy Sauce, Honey", 1900, "uklrhp0tqmyymkrwaau7/1616623317.jpg", ["Chicken", "Halal"], False),
    ],
    "soups": [
        ("Hot & Sour Soup", "Tofu, Wood Ear Mushrooms, Egg, Bamboo Shoots", 600, "le98a0it093djefg6rgf/1616623426.jpg", [], False),
        ("Pork Wontons Soup", "Handmade Pork Wontons in Clear Broth", 700, "e23ell2qfqozlcm21fai/1616623456.jpg", ["Pork"], False),
        ("Shrimp Wontons Soup", "Handmade Shrimp Wontons in Clear Broth", 700, "johz24dijch9eo4amdxn/1616623463.jpg", ["Seafood"], False),
        ("Chicken Sweet Corn Soup", "Diced Chicken, Sweet Corn, Egg", 800, "xa5tlqxa7cbcqdwlqloj/1616623391.jpg", ["Chicken"], False),
        ("Crab Meat Corn Soup", "Crab Meat, Sweet Corn, Egg", 800, "moowj2neok3aztvuhxzo/1616623396.jpg", ["Seafood"], False),
        ("Crab Meat Fish Maw Soup", "Egg White, Crab Meat, Red Vinegar", 900, "krxogba2kc7cmtquhght/1616623409.jpg", ["Seafood"], False),
    ],
    "dim-sum": [
        ("Pork Siu Mai", "6 pcs, Pork, Shrimp, Shiitake Mushroom", 1500, "j53dinvvncbytj6mcbqc/1663910881.jpg", ["Pork"], False),
        ("Prawn Har Gow", "6 pcs, Shrimp, Bamboo Shoot, Crystal Wrapper", 1500, "acfbpedigesfuiyablue/1663910888.jpg", ["Seafood"], False),
        ("Xiao Long Bao", "6 pcs, Pork, Soup Broth, Ginger", 1500, "johx4wncpbq8a8kqzewi/1665207414.jpg", ["Pork"], False),
        ("Chicken Dumpling", "4 pcs, Chicken, Ginger, Garlic", 1200, "", ["Chicken", "Halal"], False),
        ("Crystal Dumpling", "4 pcs, Mixed Vegetables, Crystal Wrapper", 1200, "wgou2mk81kigcnkqj5wm/1665521112.jpg", ["Vegetarian"], False),
    ],
    "seafood": [
        ("Ginger Scallion Cod", "Golden Fried Cod Fillet, Ginger Scallion Seasoning", 2300, "bnrqvwlcpuzfrsvr7dxy/1692985780.jpg", ["Seafood"], False),
        ("Cod with Broccoli", "Cod Fillet, Broccoli, Oyster Sauce", 2500, "", ["Seafood"], False),
        ("Seafood Ma Po Tofu", "Cod Fillet, Shrimp, Silken Tofu, House Sambal", 2500, "uxwzjbxswv7preeaevpp/1692986227.jpg", ["Seafood", "Spicy"], False),
        ("Spicy Squid", "House Sambal, Bell Pepper, Onion", 2000, "fk4fvte2rizvho7g6rap/1616623761.jpg", ["Seafood", "Spicy"], False),
    ],
    "chicken": [
        ("Ginger Onion Chicken", "Fresh Ginger, Green Onions, Soy Sauce", 2100, "", ["Chicken", "Halal"], False),
        ("Lemon Chicken", "Lemon Sauce, Garlic", 2200, "mf2zayta9costsdpikdx/1616624131.jpg", ["Chicken", "Halal"], False),
        ("Curry Chicken", "Yellow Curry, Coconut Milk, Potato, Onion", 2100, "oanxxksrvwxbup586nwl/1616624077.jpg", ["Chicken", "Spicy", "Halal"], False),
    ],
    "beef": [
        ("Garlic Beef Tenderloin", "Garlic, Soy Sauce, Butter", 2200, "gwmenbptdwsqb330ik17/1664085547.jpg", ["Beef", "Halal"], False),
        ("Sichuan Beef Tenderloin", "Szechuan Peppercorn, Chili, Garlic", 2500, "jndak9yqsjs3l6refh2x/1616624014.jpg", ["Beef", "Spicy"], False),
        ("Beef with Broccoli", "Broccoli, Garlic, Oyster Sauce", 2500, "xion7a0ypvv7icqamyoj/1616623931.jpg", ["Beef"], False),
    ],
    "duck": [
        ("Roasted Duck", "Half Duck, Five Spice, Hoisin", 2800, "jf4sdjvgfz8s4lwwvv9m/1664085483.jpg", ["Duck"], False),
    ],
    "vegetables": [
        ("Spicy Fried Tofu", "Golden Fried Tofu, House Sambal, Garlic", 1600, "whqhj0k4njrcbgbhars0/1616624640.jpg", ["Vegetarian", "Spicy"], False),
        ("Spicy Green Beans", "Green Beans, House Sambal, Garlic", 1700, "kv8n3xkctcsduetut4pe/1616624775.jpg", ["Vegetarian", "Spicy"], False),
        ("Braised Shiitake Mushrooms", "Shiitake Mushrooms, Bok Choy, Oyster Sauce", 2000, "v0jjdfa50wz0vz3jmbgv/1614833428.jpg", ["Vegetarian"], False),
        ("Mixed Vegetables", "Seasonal Mix, Garlic, Oyster Sauce", 1800, "cbyhn1hyepz6fxvznakm/1668055152.jpg", ["Vegetarian"], False),
        ("Ginger Gai-Lan", "Chinese Broccoli, Fresh Ginger, Garlic", 1800, "dcofpsongpmco8n6cnnj/1616624678.jpg", ["Vegetarian"], False),
        ("Garlic Bok Choy", "Bok Choy, Garlic", 1900, "xvk7sdrji02ogmhgtw4a/1616624657.jpg", ["Vegetarian"], False),
        ("Garlic Snow Pea Tips", "Snow Pea Tips, Garlic, Oyster Sauce", 2200, "", ["Vegetarian"], False),
        ("Stir Fry Eggplant", "Green Beans, Chinkiang Black Vinegar, House Sambal", 1900, "cv8l8xb5bictjnoh09au/1692985922.jpg", ["Vegetarian", "Spicy"], False),
    ],
    "rice": [
        ("Hong Shing Fried Rice", "Shrimp, Chicken, BBQ Pork, Egg, Green Peas", 1900, "dipfrj8q5suslfif9prq/1616624477.jpg", ["Chicken", "Seafood", "Halal"], False),
        ("Chicken Fried Rice", "Chicken, Egg, Green Peas, Carrots", 1800, "rdmiscpgvzbjsjnrhfcm/1616624458.jpg", ["Chicken", "Halal"], False),
        ("Truffle Duck Fried Rice", "Duck, Truffle Oil, Egg, Green Peas", 2500, "", ["Duck"], False),
        ("XO Seafood Fried Rice", "XO Sauce, Shrimp, Squid, Scallop, Carrots, Egg", 2300, "rcp2gfsoa8cbgpct8yxf/1663906644.png", ["Seafood", "Spicy"], False),
        ("Vegetable Fried Rice", "Mixed Vegetables, Egg, Soy Sauce", 1900, "kpo5r27px4xqjea0gelq/1616624584.jpg", ["Vegetarian"], False),
        ("Steamed Jasmine Rice", "Jasmine Steamed Rice", 300, "q7qjopbqkddvidlxnfhg/1641254763.jpg", ["Vegetarian", "Gluten-Free"], False),
    ],
    "noodles": [
        ("Cantonese Fried Noodles", "Pan Fried Egg Noodles, Chicken, Beef, Seafood, Mixed Vegetables", 2300, "bty4enpgsp15c4hbaohl/1616624947.jpg", ["Chicken", "Beef", "Seafood", "Halal"], False),
        ("Stir Fry Egg Noodles", "Egg Noodles, Bean Sprouts, Soy Sauce", 1700, "thjeh57vjfpfcazx5jrg/1664085827.jpg", ["Vegetarian"], False),
        ("Rice Noodles with Beef", "Flat Rice Noodles, Beef, Bean Sprouts, Soy Sauce", 1900, "i5ksw0uozo7hgnibdzsl/1668053657.jpg", ["Beef"], False),
        ("Vegetable Fried Noodles", "Egg Noodles, Mixed Vegetables, Soy Sauce", 1900, "efnhb3rjxcmushkho4cl/1616625102.jpg", ["Vegetarian"], False),
        ("Shanghai Noodles", "Thick Noodles, Chicken, Seafood, Bok Choy, Soy Sauce", 2000, "eeklplrvbzbmqkhghxiy/1616625077.jpg", ["Chicken", "Seafood", "Spicy"], False),
        ("Singapore Noodles", "Rice Vermicelli, Shrimp, Curry, Bean Sprouts", 1900, "wsriu9jbpuwfgjyqq6jy/1616625082.jpg", ["Seafood", "Spicy"], False),
    ],
}


async def seed_menu(force: bool = False):
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        session: AsyncSession

        existing = await session.execute(select(Category).limit(1))
        if existing.scalar_one_or_none() and not force:
            print("Menu already seeded — skipping. Use --force to re-seed.")
            return

        if force:
            from sqlalchemy import delete
            await session.execute(delete(MenuItem))
            await session.execute(delete(Category))
            await session.commit()
            print("Cleared existing menu.")

        category_map: dict[str, str] = {}
        for i, cat_data in enumerate(CATEGORIES):
            cat = Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                image_url=cat_data.get("image_url"),
                sort_order=cat_data.get("sort_order", i),
            )
            session.add(cat)
            await session.flush()
            category_map[cat.slug] = cat.id

        for slug, products in PRODUCTS_BY_CATEGORY.items():
            cat_id = category_map.get(slug)
            if not cat_id:
                continue
            for j, (name, desc, price_cents, image_key, tags, popular) in enumerate(products):
                image_url = f"{CLOUD_ASSET_BASE}/{image_key}" if image_key else None
                item = MenuItem(
                    category_id=cat_id,
                    name=name,
                    description=desc,
                    price_cents=price_cents,
                    tags=",".join(tags) if tags else None,
                    popular=popular,
                    sort_order=j,
                )
                session.add(item)

        await session.commit()
        total_items = sum(len(v) for v in PRODUCTS_BY_CATEGORY.values())
        print(f"Seeded {len(CATEGORIES)} categories and {total_items} menu items.")
