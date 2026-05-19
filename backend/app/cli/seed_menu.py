"""Seed the database with the full HongShing menu — categories and products."""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import Base, engine as db_engine
from app.models.menu import Category, MenuItem

settings = get_settings()

CLOUD_ASSET_BASE = "https://cloud-assets.orderingplus.com/image/upload/f_auto,q_auto,h_600,c_limit/hongshing"

CATEGORIES = [
    {"name": "New Dishes", "slug": "new-dishes", "sort_order": 0, "image_url": f"{CLOUD_ASSET_BASE}/y7zqp8cgjpasjwara6ca/1664201121.jpg"},
    {"name": "Starters", "slug": "starters", "sort_order": 1, "image_url": f"{CLOUD_ASSET_BASE}/j3sh7ookemnh8czbtwwh/1664201131.jpg"},
    {"name": "Soup", "slug": "soup", "sort_order": 2, "image_url": f"{CLOUD_ASSET_BASE}/f9qxbchb2yfovx7d2tps/1664289081.jpg"},
    {"name": "Seafood", "slug": "seafood", "sort_order": 3, "image_url": f"{CLOUD_ASSET_BASE}/f0xpza2fhteonprqhouc/1664201149.jpg"},
    {"name": "Poultry", "slug": "poultry", "sort_order": 4, "image_url": f"{CLOUD_ASSET_BASE}/sovxx4efbnwe7lhejhtn/1664289111.jpg"},
    {"name": "Beef", "slug": "beef", "sort_order": 5, "image_url": f"{CLOUD_ASSET_BASE}/ghcjer7grwutpyj3xsl9/1664289076.jpg"},
    {"name": "Vegetables", "slug": "vegetables", "sort_order": 6, "image_url": f"{CLOUD_ASSET_BASE}/ti8aaxgrx9voxl00fdti/1664201206.jpg"},
    {"name": "Noodles", "slug": "noodles", "sort_order": 7, "image_url": f"{CLOUD_ASSET_BASE}/x03cmw3u5xbgu7gbrtnz/1664289090.jpg"},
    {"name": "Rice", "slug": "rice", "sort_order": 8, "image_url": None},
    {"name": "Refreshments", "slug": "refreshments", "sort_order": 9, "image_url": None},
    {"name": "Dim Sum", "slug": "dim-sum", "sort_order": 10, "image_url": None},
    {"name": "Additional Sauces", "slug": "additional-sauces", "sort_order": 11, "image_url": None},
]

PRODUCTS_BY_CATEGORY = {
    "new-dishes": [
        ("General Tao Lobster", "Golden Fried Lobster, House General Tao Sauce, Hoisin", 4500, "kwlxn4m60yp89l33cl5r/1640965963.jpg"),
        ("Lobster E-Fu Noodles", "Golden Fried Lobster, E-Fu Wheat Noodles, Ginger, Garlic, Green Scallions", 5000, "y4lcidii61qaukdyrbzx/1640965733.jpg"),
        ("XO Seafood Fried Rice", "XO Sauce, Shrimp, Squid, Scallop, Carrots, Green Peas, Egg, Soya", 2200, "rcp2gfsoa8cbgpct8yxf/1663906644.png"),
        ("Typhoon Style Lobster", "Golden Fried Lobster, Garlic, Pork & Prawn XO Sauce, Green Scallions, Maggi Sauce", 4500, "bxmepmkx8sybmyohcxga/1664289194.jpg"),
        ("Ginger Scallion Cod", "Golden fried cod fillet tossed with our signature Ginger Scallion Seasoning!", 2400, "bnrqvwlcpuzfrsvr7dxy/1692985780.jpg"),
        ("Stir Fry Eggplant", "Green Beans, Chinkiang Black Vinegar, House Sambal", 1900, "cv8l8xb5bictjnoh09au/1692985922.jpg"),
        ("Seafood Ma Po Tofu", "Cod Fillet, Shrimp, Silken Tofu, House Sambal", 2500, "uxwzjbxswv7preeaevpp/1692986227.jpg"),
    ],
    "starters": [
        ("Honey Garlic Chicken Wings", "Garlic, Soy Sauce", 1900, "uklrhp0tqmyymkrwaau7/1616623317.jpg"),
        ("Spicy Dry Chicken Wings", "House Sambal, Bell Pepper", 1900, "rztvolqu13keh814lhmb/1616623355.jpg"),
        ("Golden Fried Chicken Wings", "Black Pepper, Lemon", 1800, "tvyu8ygw5hrmc0kyfnzu/1616623255.jpg"),
        ("Deep Fried Shrimp Wontons", "6 pieces, Shrimp, Wood Ear Mushrooms, Sweet Sour Sauce", 1400, "axtamzz4spr1hzpkfxp4/1640965598.jpg"),
        ("Ma La Chicken Wings", "Szechuan Peppercorn, Black Cardamon, Cumin", 1900, "wsoyutsc08jhisps8r60/1616623380.jpg"),
        ("Chicken Balls", "6 pieces, Golden Fried Batter Wrapped Chicken Breast, Sweet Sour Sauce", 1500, "tonmzyu53xgpvhajicvj/1616623212.jpg"),
        ("Vegetable Spring Rolls", "Cabbage, Carrots, Mixed Vegetables", 300, "jhgiofk0di7f32yjzwws/1640965996.jpg"),
        ("Shrimp Roll", "3 Pieces. Golden Fried Rice Wrapper, Minced Shrimp, Sweet and Sour Sauce", 600, "p5gofpyj9fg6dyds5e6l/1616623325.jpg"),
    ],
    "soup": [
        ("Crab Meat Corn Soup", "Crab Meat, Sweet Corn, Egg", 800, "moowj2neok3aztvuhxzo/1616623396.jpg"),
        ("Crab Meat Fish Maw Soup", "Egg White, Crab Meat, Red Vinegar", 900, "krxogba2kc7cmtquhght/1616623409.jpg"),
        ("Chicken Sweet Corn Soup", "Diced Chicken, Sweet Corn, Egg", 800, "xa5tlqxa7cbcqdwlqloj/1616623391.jpg"),
        ("Shrimp Wonton Soup", "Handmade shrimp wontons in clear broth", 700, "johz24dijch9eo4amdxn/1616623463.jpg"),
        ("Pork Wonton Soup", "Handmade pork wontons in clear broth", 700, "e23ell2qfqozlcm21fai/1616623456.jpg"),
        ("Hot & Sour Soup", "Tofu, wood ear mushrooms, egg, bamboo shoots", 600, "le98a0it093djefg6rgf/1616623426.jpg"),
    ],
    "seafood": [
        ("Spicy Dry Lobster", "House Sambal, Bell Pepper", 4500, "t6r1t8tjnarh5wvpunp3/1664289020.jpg"),
        ("Deep Fried Spicy Cod", "Golden Fried Cod, House Sambal, Bell Pepper", 2500, "dgdu34rh7giirkhh8bdb/1668051471.jpg"),
        ("Spicy Shrimps", "Jumbo Shrimp, House Sambal, Bell Pepper", 2200, "xvf6ry67dgussmkhtcbx/1599685187.jpg"),
        ("Szechuan Lobster", "Szechuan Peppercorn, Garlic, Ginger, Chili", 4500, "yninvymjlac3l54evyuh/1616623837.jpg"),
        ("Black Bean Lobster", "Fermented Black Bean, Garlic, Ginger, Bell Pepper", 4500, "w5mn9yfqahonzr4cdfid/1616623506.jpg"),
        ("Ginger Onion Lobster", "Fresh Ginger, Green Onions, Soy Sauce", 4500, "kbara2fxlysibia4358h/1640965752.jpg"),
        ("Spicy Squid", "House Sambal, Bell Pepper, Onion", 2200, "fk4fvte2rizvho7g6rap/1616623761.jpg"),
    ],
    "poultry": [
        ("Curry Chicken", "Yellow Curry, Coconut Milk, Potato, Onion", 1700, "oanxxksrvwxbup586nwl/1616624077.jpg"),
        ("General Tao Chicken", "House General Tao Sauce, Hoisin, House Sambal", 2000, "gfp0ooz5kqitynqolekb/1616624100.jpg"),
        ("Lemon Chicken", "Lemon Sauce, Garlic", 1800, "mf2zayta9costsdpikdx/1616624131.jpg"),
        ("Sweet & Sour Chicken", "Sweet and Sour Sauce, Bell Pepper, Pineapple", 1700, "evcrg50opsswowksimf1/1641255375.jpg"),
        ("Black Bean Chicken", "Fermented Black Bean, Garlic, Ginger", 1700, "yv1xiagropvq9efkolkq/1616624034.jpg"),
        ("Chili Chicken", "Bird's Eye Chili, Garlic, Soy Sauce", 1800, "qoms53lwuhb4nmdmm26q/1616624244.jpg"),
        ("Oven Roasted Duck", "Half Duck, Five Spice, Hoisin", 2600, "jf4sdjvgfz8s4lwwvv9m/1664085483.jpg"),
    ],
    "beef": [
        ("Beef with Gai Lan", "Chinese Broccoli, Garlic, Oyster Sauce", 1800, "nwc35lrxzmhdoskk0bv3/1616623938.jpg"),
        ("Black Bean Beef", "Fermented Black Bean, Garlic, Ginger", 1800, "nxezr7nbvyzg72akppgv/1616623952.jpg"),
        ("Sichuan Beef Tenderloin", "Szechuan Peppercorn, Chili, Garlic", 2400, "jndak9yqsjs3l6refh2x/1616624014.jpg"),
        ("Crispy Beef", "Golden Fried Beef Strips, Sweet Soy Glaze", 2000, "eiitevflt0zd5ehetqey/1616623989.jpg"),
        ("Beef with Broccoli", "Broccoli, Garlic, Oyster Sauce", 1800, "xion7a0ypvv7icqamyoj/1616623931.jpg"),
        ("Garlic Beef Tenderloin", "Garlic, Soy Sauce, Butter", 2400, "gwmenbptdwsqb330ik17/1664085547.jpg"),
    ],
    "vegetables": [
        ("Deep Fried Spicy Tofu", "Golden Fried Tofu, House Sambal, Garlic", 1600, "whqhj0k4njrcbgbhars0/1616624640.jpg"),
        ("Garlic Broccoli", "Broccoli, Garlic, Oyster Sauce", 1500, "xxujym125wh81canqpyy/1616624665.jpg"),
        ("Braised Shiitake Mushrooms", "Shiitake Mushrooms, Bok Choy, Oyster Sauce", 1700, "v0jjdfa50wz0vz3jmbgv/1614833428.jpg"),
        ("Garlic Bok Choy", "Bok Choy, Garlic", 1500, "xvk7sdrji02ogmhgtw4a/1616624657.jpg"),
        ("Spicy Green Beans", "Green Beans, House Sambal, Garlic", 1500, "kv8n3xkctcsduetut4pe/1616624775.jpg"),
        ("Mixed Seasonal Vegetables", "Seasonal Mix, Garlic, Oyster Sauce", 1600, "cbyhn1hyepz6fxvznakm/1668055152.jpg"),
        ("Ginger Gai-Lan", "Chinese Broccoli, Fresh Ginger, Garlic", 1500, "dcofpsongpmco8n6cnnj/1616624678.jpg"),
    ],
    "noodles": [
        ("Rice Noodles with Beef", "Flat Rice Noodles, Beef, Bean Sprouts, Soy Sauce", 1600, "i5ksw0uozo7hgnibdzsl/1668053657.jpg"),
        ("Beef Fried Noodles", "Egg Noodles, Beef, Soy Sauce", 1600, "ehhwjqidoi5buizjb5wv/1641322850.jpg"),
        ("Seafood Fried Noodles", "Egg Noodles, Shrimp, Squid, Scallop", 1800, "l9zmdv8s70kkgsiindxe/1616625064.jpg"),
        ("Mixed Vegetables Fried Noodles", "Egg Noodles, Mixed Vegetables, Soy Sauce", 1500, "efnhb3rjxcmushkho4cl/1616625102.jpg"),
        ("Shanghai Noodles", "Thick Noodles, Pork, Bok Choy, Soy Sauce", 1600, "eeklplrvbzbmqkhghxiy/1616625077.jpg"),
        ("Singapore Noodles", "Rice Vermicelli, Shrimp, BBQ Pork, Curry", 1600, "wsriu9jbpuwfgjyqq6jy/1616625082.jpg"),
        ("Chicken Fried Noodles", "Egg Noodles, Chicken, Soy Sauce", 1500, "pxsg7nwpewlvltccabd7/1616624962.jpg"),
        ("Stir Fried Egg Noodles", "Egg Noodles, Bean Sprouts, Soy Sauce", 1400, "thjeh57vjfpfcazx5jrg/1664085827.jpg"),
        ("Cantonese Fried Noodles", "Pan Fried Egg Noodles, Mixed Vegetables", 1500, "bty4enpgsp15c4hbaohl/1616624947.jpg"),
    ],
    "rice": [
        ("Hong Shing Fried Rice", "Shrimp, Chicken, BBQ Pork, Egg, Green Peas", 1500, "dipfrj8q5suslfif9prq/1616624477.jpg"),
        ("Steamed Rice", "Jasmine Steamed Rice", 300, "q7qjopbqkddvidlxnfhg/1641254763.jpg"),
        ("Chicken Fried Rice", "Chicken, Egg, Green Peas, Carrots", 1400, "rdmiscpgvzbjsjnrhfcm/1616624458.jpg"),
        ("Shrimp Fried Rice", "Shrimp, Egg, Green Peas, Carrots", 1500, "mypybvcci2lbb5wnxzwo/1616624554.jpg"),
        ("Mixed Vegetable Fried Rice", "Mixed Vegetables, Egg, Soy Sauce", 1300, "kpo5r27px4xqjea0gelq/1616624584.jpg"),
    ],
    "refreshments": [
        ("Ginger Ale", "355ml Can", 200, "bwz2nkpxczbosj6r4wr7/1641254503.jpg"),
        ("Bottled Water", "500ml", 200, "iplslkqwoubaikxuawwp/1641254547.jpg"),
        ("Sprite", "355ml Can", 200, "qjmpkldnmvdtuyadgaix/1641254514.jpg"),
        ("Coke", "355ml Can", 200, "uixrir3fabyiw0lug714/1641254492.jpg"),
    ],
    "dim-sum": [
        ("Prawn Har Gow", "4 pieces, Shrimp, Bamboo Shoot, Crystal Wrapper", 800, "acfbpedigesfuiyablue/1663910888.jpg"),
        ("Pork Siu Mai", "4 pieces, Pork, Shrimp, Shiitake Mushroom", 800, "j53dinvvncbytj6mcbqc/1663910881.jpg"),
        ("Xiao Long Bao", "4 pieces, Pork, Soup Broth, Ginger", 700, "johx4wncpbq8a8kqzewi/1665207414.jpg"),
        ("Vegetable Crystal Dumpling", "3 pieces, Mixed Vegetables, Crystal Wrapper", 700, "wgou2mk81kigcnkqj5wm/1665521112.jpg"),
        ("Dim Sum Platter", "2 Har Gow, 2 Siu Mai, 2 Xiao Long Bao", 1700, "fjn7pk1le4saxxhkhniu/1665521084.jpg"),
    ],
    "additional-sauces": [
        ("Sweet & Sour Sauce", None, 200, "id2tsnprizkqy82nghgy/1641254675.jpg"),
        ("Lemon Sauce", None, 200, "ewywrifhbpayl14whyyx/1641254668.jpg"),
        ("General Tao Sauce", None, 200, "zibkvg5gfvroyfc9ytrs/1641254627.jpg"),
        ("Black Bean Sauce", None, 200, "e8ntdiv8yhpodpxfk3e8/1640965556.jpg"),
        ("Curry Sauce", None, 200, "f0yhz6fg93086u8nss0t/1640965570.jpg"),
        ("Chili Oil", None, 200, "skb1kxflgupznxfvqk5s/1641254578.jpg"),
        ("Green Scallion Sauce", None, 200, "fp3ogysax7v7ykbnvbal/1641254646.jpg"),
    ],
}


async def seed_menu():
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.database import async_session
    async with async_session() as session:
        session: AsyncSession

        existing = await session.execute(select(Category).limit(1))
        if existing.scalar_one_or_none():
            print("Menu already seeded — skipping.")
            return

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
            for j, (name, desc, price_cents, image_key) in enumerate(products):
                image_url = f"{CLOUD_ASSET_BASE}/{image_key}" if image_key else None
                item = MenuItem(
                    category_id=cat_id,
                    name=name,
                    description=desc,
                    price_cents=price_cents,
                    image_url=image_url,
                    sort_order=j,
                )
                session.add(item)

        await session.commit()
        total_items = sum(len(v) for v in PRODUCTS_BY_CATEGORY.values())
        print(f"Seeded {len(CATEGORIES)} categories and {total_items} menu items.")


if __name__ == "__main__":
    asyncio.run(seed_menu())
