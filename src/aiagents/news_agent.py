import asyncio
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool
from agents.run import RunConfig
from dotenv import load_dotenv
import os
import httpx
from pydantic import BaseModel
from datetime import datetime, timedelta

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
news_api_key = os.getenv("NEWS_API_KEY")

provider = AsyncOpenAI(
    api_key=gemini_api_key,
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

async def fetch_news(q: str, days: int = 3):
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days)
    url = (
        f"https://newsapi.org/v2/everything?q={q}"
        f"&from={start_date}"
        f"&to={today}"
        f"&sortBy=popularity"
        f"&apiKey={news_api_key}"
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        articles = [
            {
                "title": a["title"],
                "description": a.get("description"),
                "url": a["url"],
                "content": a.get("content"),
                "publishedAt": a.get("publishedAt"),
            }
            for a in data.get("articles", [])[:3]
        ]
        return {"status": data.get("status"), "totalResults": data.get("totalResults"), "articles": articles}

@function_tool
async def get_news(q: str, days: int = 3):
    return await fetch_news(q, days)

class Article(BaseModel):
    title: str
    description: str | None
    url: str
    content: str | None
    publishedAt: str | None

class Output(BaseModel):
    status: str
    totalResults: int
    articles: list[Article]

agent = Agent(
    name="NewsAgent",
    instructions="You are a News Assistant. Always use the get_news tool to fetch news.",
    tools=[get_news],
    output_type=Output,
)

async def main():
    result = await Runner.run(
        agent,
        input="OpenAI",
        run_config=run_config,
    )
    print(result.final_output.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
