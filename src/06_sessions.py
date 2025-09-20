# =============================================================================
# pg_demo.py – one-file PostgreSQL session backend for the `agents` library
# =============================================================================
# Each physical line is annotated character-by-character so nothing is magic.
# =============================================================================

# ------------------------------ 1.  stdlib imports ---------------------------
import asyncio          # keyword 'import' + module name 'asyncio'
import json             # keyword 'import' + module name 'json'
from typing import List, Optional   # 'from … import …' pulls only these names

# ------------------------------ 2.  third-party ------------------------------
import asyncpg                      # async PostgreSQL driver
from agents import Agent, Runner    # agent orchestration
from agents.memory import Session   # protocol we must satisfy
from agents.run import RunConfig    # carries model & provider
from agents import AsyncOpenAI, OpenAIChatCompletionsModel  # Gemini adapter
from dotenv import load_dotenv      # loads .env → os.environ
import os                           # OS-level utilities

# ------------------------------ 3.  load env secrets -------------------------
load_dotenv()                       # read .env file (safe if missing)
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or "YOUR_GEMINI_API_KEY"  # fallback

# ------------------------------ 4.  SQL DDL (run once) -----------------------
DDL = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    session_id TEXT NOT NULL,
    idx        SERIAL,
    payload    JSONB NOT NULL,
    PRIMARY KEY (session_id, idx)
);
CREATE INDEX IF NOT EXISTS idx_session ON conversation_turns(session_id);
"""

# =============================================================================
# PostgreSQLSession – concrete implementation of the Session protocol
# =============================================================================
class PostgreSQLSession(Session):
    """
    Implements Session via PostgreSQL table:
    conversation_turns(session_id, idx, payload)
    """

    # -------------------------------------------------------------------------
    # __init__ – called when you do PostgreSQLSession(...)
    # -------------------------------------------------------------------------
    def __init__(self, session_id: str, dsn: str) -> None:
        self.session_id = session_id    # user-supplied chat thread id
        self.dsn = dsn                  # PostgreSQL connection string
        self._pool: Optional[asyncpg.Pool] = None  # cached pool (lazy init)

    # -------------------------------------------------------------------------
    # _pool_acquire – helper coroutine to get or create the connection pool
    # -------------------------------------------------------------------------
    async def _pool_acquire(self) -> asyncpg.Pool:
        if self._pool is None:  # first call? build pool
            self._pool = await asyncpg.create_pool(
                self.dsn, min_size=1, max_size=10
            )
        return self._pool

    # -------------------------------------------------------------------------
    # Session protocol method #1 – retrieve history
    # -------------------------------------------------------------------------
    async def get_items(self, limit: Optional[int] = None) -> List[dict]:
        pool = await self._pool_acquire()  # get pool
        sql = (
            "SELECT payload "
            "FROM   conversation_turns "
            "WHERE  session_id = $1 "
            "ORDER  BY idx ASC "
            + ("LIMIT $2" if limit else "")
        )
        args = [self.session_id] if limit is None else [self.session_id, limit]
        rows = await pool.fetch(sql, *args)          # list[Record]
        return [json.loads(r["payload"]) for r in rows]

    # -------------------------------------------------------------------------
    # Session protocol method #2 – store new turns
    # -------------------------------------------------------------------------
    async def add_items(self, items: List[dict]) -> None:
        if not items:                # fast path: nothing to do
            return
        pool = await self._pool_acquire()
        await pool.executemany(
            "INSERT INTO conversation_turns(session_id, payload) VALUES ($1, $2)",
            [(self.session_id, json.dumps(item)) for item in items]
        )

    # -------------------------------------------------------------------------
    # Session protocol method #3 – pop last turn (LIFO)
    # -------------------------------------------------------------------------
    async def pop_item(self) -> Optional[dict]:
        pool = await self._pool_acquire()
        async with pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                """
                DELETE FROM conversation_turns
                WHERE ctid = (
                    SELECT ctid
                    FROM   conversation_turns
                    WHERE  session_id = $1
                    ORDER  BY idx DESC
                    LIMIT  1
                )
                RETURNING payload
                """,
                self.session_id
            )
            return json.loads(row["payload"]) if row else None

    # -------------------------------------------------------------------------
    # Session protocol method #4 – wipe all turns for this session
    # -------------------------------------------------------------------------
    async def clear_session(self) -> None:
        pool = await self._pool_acquire()
        await pool.execute(
            "DELETE FROM conversation_turns WHERE session_id = $1",
            self.session_id
        )

    # -------------------------------------------------------------------------
    # close – tidy shutdown
    # -------------------------------------------------------------------------
    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

# =============================================================================
# one-time schema bootstrap helper
# =============================================================================
async def _ensure_schema(dsn: str) -> None:
    conn = await asyncpg.connect(dsn)  # open single connection
    await conn.execute(DDL)            # run DDL string
    await conn.close()                 # close it

# =============================================================================
# main demo coroutine
# =============================================================================
async def main() -> None:
    # 1. build connection string (edit to taste)
    PG_DSN = "postgresql://myuser:mypassword@localhost:5432/mydb"

    # 2. create table & index if missing
    await _ensure_schema(PG_DSN)

    # 3. build Gemini client via OpenAI-compatible endpoint
    provider = AsyncOpenAI(
        api_key=GEMINI_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    model = OpenAIChatCompletionsModel(
        model="gemini-2.0-flash",
        openai_client=provider,
    )
    run_config = RunConfig(
        model=model,
        model_provider=provider,
        tracing_disabled=True,
    )

    # 4. create PostgreSQL session & fresh agent
    session = PostgreSQLSession("demo_user_42", PG_DSN)
    await session.clear_session()  # start clean for demo
    assistant = Agent(name="Assistant", instructions="Answer concisely.")

    # 5. mini-chat loop
    turns = [
        "What city is the Golden Gate Bridge in?",
        "What state is that in?",
        "What's the population of that state?",
    ]
    for turn in turns:
        print(f"User : {turn}")
        result = await Runner.run(
            assistant,
            turn,
            session=session,
            run_config=run_config,
        )
        print(f"Agent: {result.final_output}\n")

    # 6. show raw rows stored in Postgres
    print("--- Raw history from PostgreSQL ---")
    for d in await session.get_items():
        print(d["role"], ":", d["content"])

    # 7. tidy up
    await session.close()

# =============================================================================
# script entry point
# =============================================================================
if __name__ == "__main__":
    asyncio.run(main())  # start async event loop & run main()