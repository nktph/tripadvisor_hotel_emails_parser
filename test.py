from main import main
import asyncio


async def parse(link: str, limit: int):
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(main(country_link=link, limit=limit), loop)
    while True:
        print("Чё-то происходит параллельно пока парсер работает")
        await asyncio.sleep(5)



asyncio.run(parse(f"https://www.tripadvisor.com/Hotels-g255060-Sydney_New_South_Wales-Hotels.html", 5))