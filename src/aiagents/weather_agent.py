import asyncio
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool
from agents.run import RunConfig
from dotenv import load_dotenv
import os
from agents import enable_verbose_stdout_logging
import httpx
from pydantic import BaseModel

# enable_verbose_stdout_logging()

# Load the environment variables from the .env file
load_dotenv()

# Set up the your Gemini API key
gemini_api_key = os.getenv("GEMINI_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")

# 1 Set up the provider to use the Gemini API Key
provider = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# 2 Set up the model to use the provider
model = OpenAIChatCompletionsModel(
    model='gemini-2.0-flash',
    openai_client=provider,
)

# 3 Set up the run configuraion
run_config = RunConfig(
    model=model,
    model_provider=provider,
    tracing_disabled=True,
)


async def fetch_weather(query: str):
    url = (
        f"http://api.weatherapi.com/v1/current.json?key={weather_api_key}&q={query}&aqi=no"
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return {
            "location": data["location"]["name"],
            "temperature": data["current"]["temp_c"],
            "weather": data["current"]["condition"]["text"]
        }

@function_tool
async def get_weather(query: str):
    return await fetch_weather(query)

class Weather(BaseModel):
    location: str
    temperature: float
    weather: str


agent = Agent(
    name="agent",
    instructions="You are a helpful assistant.",
    tools=[get_weather],
    output_type=Weather
)

async def main():
    # 5 Set up the runner to use the agent
    result = await Runner.run(
        agent,
        input="what is the weather in london",
        run_config=run_config,
    )
    print(result.final_output.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())