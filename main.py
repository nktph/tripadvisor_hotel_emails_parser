import time

import requests
from bs4 import BeautifulSoup


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
headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.47'}


# Функция проверки почты отеля (принимает ссылку на страницу отеля)
def check_email(hotel_link: str):
    global EMAILS_COUNT
    # Получаем страницу отеля
    resp = requests.get(hotel_link,
                        timeout=10,
                        headers=headers)

    # Почта может храниться в двух местах html-документа, если не найдём в первом - бросит исключение и поищет во втором
    email=""
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
    # TODO: Если сверяешь спаршенные отели по почте, то проверка на наличие в бд вставляется сюда
    if email:
        with open("emails.txt", 'a') as file:
            file.write(f"{email}\n")
            EMAILS_COUNT += 1


# Функция получения ссылок на отели со страницы (принимает ссылку на страницу со списком отелей)
def get_hotels_links_from_page(page_link: str):
    # Получаем страницу со списком отелей
    resp = requests.get(page_link,
                        headers=headers)

    # Создаём объект BeautifulSoup для удобного поиска нужных тегов в html-разметке
    soup = BeautifulSoup(resp.text, "html.parser")

    # Находим все карточки отелей для получения из них информации
    divs = soup.findAll('div', class_='prw_rup prw_meta_hsx_responsive_listing ui_section listItem reducedWidth rounded')

    global EMAILS_COUNT
    # Проходим по полученным отелям
    for div in divs:
        # Если получили почт достаточно, завершаем работу
        if EMAILS_COUNT >= LIMIT:
            print(f"Спарсили {LIMIT} почт, завершение работы...")
            raise KeyboardInterrupt

        # Находим название отеля
        hotel = div.find('a', class_='property_title prominent')

        # Находим количество отзывов и переводим его из строки в число
        review_count = div.find('a', class_='review_count').text
        review_count = int(review_count.split(' reviews')[0].replace(',',''))

        # Отсеиваем отели у которых меньше отзывов, чем нам нужно (по умолчанию - 500)
        if review_count < MIN_REVIEW_COUNT:
            continue

        # Выводим название отеля и количество отзывов
        print(hotel.text.strip())
        print(f"Reviews: {review_count}")

        # Проверяем, есть ли у отеля почта
        check_email(f"https://www.tripadvisor.com{hotel['href']}")
        print()

        # Задержка для избежания блокировки от слишком частых запросов
        time.sleep(DELAY)


# Функция получения следующей страницы с отелями (принимает ссылку на текущую страницу)
def get_next_page(current_page_link: str):
    # Получаем страницу
    resp = requests.get(current_page_link,
                        timeout=10,
                        headers=headers)
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
def go_to_pages(link: str):
    # Пока мы получаем новые ссылки от функции get_next_page(), выполняем проход по страницам
    while link:
        # На каждой странице получаем список отелей и проверяем их на наличие почты
        get_hotels_links_from_page(page_link=link)

        # Получаем новую страницу
        link = get_next_page(link)

        # Задержка для избежания блокировки от слишком частых запросов
        time.sleep(DELAY)


# Из бота вызывать вот эту функцию (Принимает ссылку на страницу выбранной страны)
# Не забудь про фильтр! (см. пример ниже)
def main(country_link: str):
    try:
        go_to_pages(country_link)
    except KeyboardInterrupt:
        print("Работа парсера завершена")
        return

if __name__ == "__main__":
    # Значение этой переменной должно быть добавлено в ссылку так, как показано в примере
    # Иначе сайт не отфильтрует отели по рейтингу (в данном примере просим сайт дать отели с рейтингом 4 и выше)
    filter = "a_trating.40-a_ufe.true-"
    # Просто пример правильного вызова функции main()
    main(f"https://www.tripadvisor.com/Hotels-g255060-{filter}Sydney_New_South_Wales-Hotels.html")