import os
import asyncio
import re
from sqlalchemy import text
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

async def async_main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_async_engine(
        re.sub(r"^postgresql:", "postgresql+psycopg:", db_url),
        echo=True
    )

    async with engine.connect() as conn:
        result = await conn.execute(text("select 'hello world'"))
        print(result.fetchall())

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(async_main())
