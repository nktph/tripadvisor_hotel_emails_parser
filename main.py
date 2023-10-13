import asyncio
from bs4 import BeautifulSoup
from database import register_hotel, get_hotel
from requests_html import AsyncHTMLSession


class ParseFinished(Exception):
    def __init__(self, text):
        self.txt = text


# Ссылки на страны отелей брать отсюда -> "https://www.tripadvisor.com/Hotels" (самый низ страницы)

# Счётчик спаршенных почт (Вручную не менять!)
EMAILS_COUNT = 0

# Сколько почт спарсить перед тем как останоситься
LIMIT = 20
# Задержка между запросами (чтобы не заблочили ip из-за слишком частых)
DELAY = 4
# Отели с меньшим числов отзывов будут отсеиваться
MIN_REVIEW_COUNT = 500

# Заголовки для запросов
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.47'}


# Функция проверки почты отеля (принимает ссылку на страницу отеля)
async def check_email(hotel_link: str, hotel_name: str):
    global EMAILS_COUNT
    # Получаем страницу отеля
    session = AsyncHTMLSession()
    resp = await session.get(hotel_link,
                             timeout=10,
                             headers=headers)


    # Почта может храниться в двух местах html-документа, если не найдём в первом - бросит исключение и поищет во втором
    email = ""
    try:
        # Вычленяем почту первым способом
        email = resp.text.split('emergencyEmail')[1].split('''\\\",''')[0].replace('\\', '').replace('":"', '')

        print(f'Email: {email if email else "no email"}')
    except IndexError:
        try:
            # Вычленяем почту вторым способом
            email = ((resp.text.split('\\"emailParts\\":[\\"')[1].split('clickTrackingUrl')[0]
                      .replace('\\', '')
                      .replace('"', '')
                      .replace(',', '')
                      .replace(']', '')))
            print(f'Email: {email if email else "no email"}')
        except IndexError:
            print("no email")

    # Если получена почта, пишем её в файл
    if email:
        register_hotel(name=hotel_name, email=email if email else "no email")
        with open("emails.txt", 'a') as file:
            file.write(f"{email}\n")
            EMAILS_COUNT += 1
    else:
        register_hotel(name=hotel_name, email="no email")


# Функция получения ссылок на отели со страницы (принимает ссылку на страницу со списком отелей)
async def get_hotels_links_from_page(page_link: str, limit: int):
    # Получаем страницу со списком отелей
    session = AsyncHTMLSession()
    resp = await session.get(page_link,
                        headers=headers)
    await session.close()

    # Создаём объект BeautifulSoup для удобного поиска нужных тегов в html-разметке
    soup = BeautifulSoup(resp.text, "html.parser")

    # Находим все карточки отелей для получения из них информации
    divs = soup.findAll('div',
                        class_='prw_rup prw_meta_hsx_responsive_listing ui_section listItem reducedWidth rounded')

    global EMAILS_COUNT
    # Проходим по полученным отелям
    for div in divs:
        # Если получили почт достаточно, завершаем работу
        if EMAILS_COUNT >= limit:
            print(f"Спарсили {limit} почт, завершение работы...")
            raise ParseFinished("Парсинг завершён")

        # Находим название отеля
        hotel = div.find('a', class_='property_title prominent')

        # Находим количество отзывов и переводим его из строки в число
        review_count = div.find('a', class_='review_count').text
        review_count = int(review_count.split(' reviews')[0].replace(',', ''))

        # Отсеиваем отели у которых меньше отзывов, чем нам нужно (по умолчанию - 500)
        if review_count < MIN_REVIEW_COUNT:
            continue

        # Выводим название отеля и количество отзывов
        hotel_name = hotel.text.strip().split('.')[1].strip()

        if get_hotel(name=hotel_name):
            print(f"Отель {hotel_name} уже есть в базе данных, пропускаем")
            continue

        print(hotel_name)
        print(f"Reviews: {review_count}")

        # Проверяем, есть ли у отеля почта
        await check_email(f"https://www.tripadvisor.com{hotel['href']}", hotel_name)
        print()

        # Задержка для избежания блокировки от слишком частых запросов
        await asyncio.sleep(DELAY)


# Функция получения следующей страницы с отелями (принимает ссылку на текущую страницу)
async def get_next_page(current_page_link: str):
    # Получаем страницу
    session = AsyncHTMLSession()
    resp = await session.get(current_page_link,
                        timeout=10,
                        headers=headers)
    await session.close()
    # Создаём объект BeautifulSoup для удобного поиска нужных тегов в html-разметке
    soup = BeautifulSoup(resp.text, "html.parser")

    # Находим ссылку на следующую страницу
    new_page_link = soup.find('a', class_='nav next ui_button primary')

    # Если ссылка существует, передаём её, если нет - значит мы на последней странице
    if new_page_link:
        return f"https://www.tripadvisor.com{new_page_link['href']}"
    else:
        return None


# Функция прохода по всем страницам выбранной страны (Принимает ссылку на первую страницу страны)
async def go_to_pages(link: str, limit: int):
    # Пока мы получаем новые ссылки от функции get_next_page(), выполняем проход по страницам
    while link:
        # На каждой странице получаем список отелей и проверяем их на наличие почты
        await get_hotels_links_from_page(page_link=link, limit=limit)

        # Получаем новую страницу
        link = await get_next_page(link)

        # Задержка для избежания блокировки от слишком частых запросов
        await asyncio.sleep(DELAY)


# Из бота вызывать вот эту функцию (Принимает ссылку на страницу выбранной страны)
# Не забудь про фильтр! (см. пример ниже)
async def main(country_link: str, limit):
    # СОЗДАНИЕ БД ВЫПОЛНИТЬ ТОЛЬКО ОДИН РАЗ, ПОСЛЕ - ЗАКОММЕНТИТЬ
    # from database import create_db
    # create_db()
    with open("emails.txt", 'w') as file:
        pass
    try:
        await go_to_pages(country_link, limit)
    except ParseFinished:
        print("Работа парсера завершена")
    finally:
        with open("emails.txt", 'r') as file:
            emails = file.readlines()
        return emails

# if __name__ == "__main__":
#     # from database import create_db
#     # create_db()
#     # Значение этой переменной должно быть добавлено в ссылку так, как показано в примере
#     # Иначе сайт не отфильтрует отели по рейтингу (в данном примере просим сайт дать отели с рейтингом 4 и выше)
#     filter = "a_trating.40-a_ufe.true-"
#     # Просто пример правильного вызова функции main()
#     main(f"https://www.tripadvisor.com/Hotels-g255060-{filter}Sydney_New_South_Wales-Hotels.html")
