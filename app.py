import cloudscraper
from bs4 import BeautifulSoup, NavigableString, Tag
import re
from collections import defaultdict
from flask import Flask, redirect, render_template, request, url_for
import base64
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

BASE_URL = "https://pahe.ink" 

def b64encode_filter(url):
    """Encode URL ke base64 URL-safe tanpa padding."""
    encoded = base64.urlsafe_b64encode(url.encode()).decode()
    return encoded.rstrip('=')

def b64decode_filter(encoded):
    """Decode base64 URL-safe (tambahkan padding jika perlu)."""
    padding = 4 - (len(encoded) % 4)
    if padding != 4:
        encoded += '=' * padding
    return base64.urlsafe_b64decode(encoded).decode()

app.jinja_env.filters['b64encode'] = b64encode_filter
app.jinja_env.filters['b64decode'] = b64decode_filter

def scrape_page(url):
    """
    Mengambil semua link film dari satu halaman (URL).
    Mengembalikan list of dict: {'href':, 'title':, 'src':}
    """
    scraper = cloudscraper.create_scraper()
    app.logger.debug(f"Scraping URL: {url}")
    response = scraper.get(url)
    if response.status_code != 200:
        raise Exception(f"Gagal mengakses halaman {url}, status: {response.status_code}")

    content = BeautifulSoup(response.text, "html.parser")
    trends = []
    movies = []

    # Ambil dari section pic-box
    pic_box = content.find("section", class_="cat-box pic-box tie-cat-254 clear pic-grid")
    if pic_box:
        pic_items = pic_box.find_all("li")
        for item in pic_items:
            tag_a = item.find("a")
            if not tag_a:
                continue
            href = tag_a.get('href', '')
            title = tag_a.get('original-title', '') or tag_a.get('title', '') or tag_a.text.strip()
            img_tag = tag_a.find("img") or item.find("img")
            src = img_tag.get('src', '') if img_tag else ''
            if href:
                trends.append({
                    'href': href,
                    'title': title,
                    'src': src
                })

    # Ambil dari section recent-box
    recent_box = content.find("section", class_="cat-box recent-box recent-blog")
    if recent_box:
        articles = recent_box.find_all("article")
        for article in articles:
            title_tag = article.find("h2", class_="post-box-title")
            title = title_tag.text.strip() if title_tag else ''
            thumbnail_tag = article.find("div", class_="post-thumbnail")
            thumbnail_src = thumbnail_tag.find("img")["src"] if thumbnail_tag and thumbnail_tag.find("img") else ''
            href_tag = article.find("a")
            href = href_tag["href"] if href_tag else ''
            if href:
                movies.append({
                    'href': href,
                    'title': title,
                    'src': thumbnail_src
                })

    return trends, movies, content


def get_total_pages(soup):
    """Ekstrak total halaman dari elemen pagination."""
    pagination = soup.find("div", class_="pagination")
    if not pagination:
        return 1
    span_pages = pagination.find("span", class_="pages")
    if not span_pages:
        return 1
    text = span_pages.text.strip()
    app.logger.debug(f"pagination text: {text}")
    match = re.search(r'of\s+([\d.,]+)', text, re.IGNORECASE)
    if match:
        app.logger.debug(f"regex match: {match}")
        number_str = match.group(1)
        return int(re.sub(r'[.,]', '', number_str))
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[-1])
    return 1


def dashboard(keyword=None, page=1):
    """
    Mengambil film dari satu halaman saja (untuk pagination).
    Jika keyword diberikan, gunakan pencarian.
    Mengembalikan list film, total halaman, dan total item (optional).
    """
    # Bangun URL untuk halaman tertentu
    if keyword:
        if page == 1:
            url = f"{BASE_URL}/?s={keyword}"
        else:
            url = f"{BASE_URL}/page/{page}/?s={keyword}"
    else:
        if page == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}/page/{page}/"

    app.logger.debug(f"Dashboard page {page} URL: {url}")

    try:
        trends, movies, soup = scrape_page(url)
    except Exception as e:
        app.logger.error(f"Error scraping page {page}: {e}")
        # Coba fallback dengan ?page=
        if keyword:
            fallback_url = f"{BASE_URL}/?s={keyword}&page={page}"
        else:
            fallback_url = f"{BASE_URL}?page={page}"
        app.logger.debug(f"Fallback URL: {fallback_url}")
        try:
            trends, movies, soup = scrape_page(fallback_url)
        except Exception as e2:
            app.logger.error(f"Fallback juga gagal: {e2}")
            return [], 1  # return empty list and total pages 1

    total_pages = get_total_pages(soup)
    return trends, movies, total_pages


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    try:
        trends, movies, total_pages = dashboard(page=page)
    except Exception as e:
        app.logger.error(f"Error di index: {e}")
        return f"Terjadi error saat scraping: {e}", 500

    return render_template(
        'index.html',
        trends=trends,
        movies=movies,
        total=len(movies)+len(trends),
        keyword=None,
        current_page=page,
        total_pages=total_pages
    )


def search_scrape(keyword, page=1):
    """
    Mengambil hasil pencarian dari halaman tertentu.
    Mengembalikan list film dan total halaman.
    """
    # Bangun URL pencarian
    if page == 1:
        url = f"{BASE_URL}/?s={keyword}"
    else:
        url = f"{BASE_URL}/page/{page}/?s={keyword}"

    scraper = cloudscraper.create_scraper()
    app.logger.debug(f"Search URL: {url}")
    response = scraper.get(url)
    if response.status_code != 200:
        raise Exception(f"Gagal mengakses halaman {url}, status: {response.status_code}")

    body = BeautifulSoup(response.text, "html.parser")

    # Ekstrak total halaman dari pagination
    pagination = body.find("div", class_="pagination")
    total_pages = 1
    if pagination:
        pages_span = pagination.find("span", class_="pages")
        if pages_span:
            text = pages_span.text.strip()
            # Contoh: "Page 1 of 100" -> ambil angka terakhir
            import re
            match = re.search(r'of\s+([\d.,]+)', text, re.IGNORECASE)
            if match:
                total_pages = int(re.sub(r'[.,]', '', match.group(1)))
            else:
                numbers = re.findall(r'\d+', text)
                if numbers:
                    total_pages = int(numbers[-1])

    # Ambil daftar film dari div.post-inner > ul
    all_links = []
    post_inner = body.find("div", class_="post-inner")
    if post_inner:
        timelines = post_inner.find_all("ul")
        for ul in timelines:
            a_tag = ul.find("a")
            h2_tag = ul.find("h2")
            img_tag = ul.find("img")
            if a_tag and h2_tag:
                href = a_tag.get("href", "")
                title = h2_tag.text.strip()
                src = img_tag.get("src", "") if img_tag else ""
                if href:
                    all_links.append({
                        'href': href,
                        'title': title,
                        'src': src
                    })

    return all_links, total_pages


@app.route('/search')
def search():
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return redirect(url_for('index'))   # jika kosong, kembali ke beranda

    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    try:
        movies, total_pages = search_scrape(keyword, page)
    except Exception as e:
        app.logger.error(f"Error di search: {e}")
        return f"Terjadi error saat pencarian: {e}", 500

    return render_template(
        'search.html',          # template baru
        movies=movies,
        total=len(movies),
        keyword=keyword,
        current_page=page,
        total_pages=total_pages
    )


@app.route('/details/<encoded_url>')
def show_details(encoded_url):
    try:
        original_url = b64decode_filter(encoded_url)
    except Exception as e:
        return f"URL tidak valid: {e}", 400

    try:
        data = details(original_url)
    except Exception as e:
        app.logger.error(f"Error di details: {e}")
        return f"Terjadi error saat scraping detail: {e}", 500

    return render_template(
        'details.html',
        thumbnail=data['thumbnail'],
        title=data['title'],
        meta=data['meta'],
        description=data['description'],
        grouped=data['grouped'],
        total_links=data['total_links']
    )


def details(url):
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url)
    if response.status_code != 200:
        raise Exception(f"Gagal mengakses halaman, status: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    thumbnail_tag = soup.find("img", class_="imdbwp__img")
    thumbnail_src = thumbnail_tag["src"] if thumbnail_tag else ""

    title_tag = soup.find("span", class_="imdbwp__title")
    title = title_tag.text.strip() if title_tag else ""

    meta_tag = soup.find("div", class_="imdbwp__meta")
    meta = meta_tag.text.strip() if meta_tag else ""

    desc_tag = soup.find("div", class_="imdbwp__teaser")
    description = desc_tag.text.strip() if desc_tag else ""

    boxes = soup.find_all("div", class_="box download")
    pattern_res = re.compile(r'\d+p.*\|.*(?:MB|GB)')
    all_links = []

    for box in boxes:
        inner_blocks = box.find_all("div", class_="box-inner-block")
        for inner in inner_blocks:
            current_res = None
            buffer = ""
            for child in inner.children:
                if isinstance(child, NavigableString):
                    buffer += child.strip()
                    if pattern_res.search(buffer):
                        current_res = buffer.strip()
                        buffer = ""
                elif isinstance(child, Tag):
                    href = child.get('href', '')
                    if child.name == 'a' and 'https://' in href:
                        if current_res:
                            all_links.append({
                                'resolution': current_res,
                                'provider': child.text.strip(),
                                'url': href
                            })
                    else:
                        buffer += child.get_text(strip=True)
                        if pattern_res.search(buffer):
                            current_res = buffer.strip()
                            buffer = ""

    grouped = defaultdict(list)
    for item in all_links:
        grouped[item['resolution']].append({
            'provider': item['provider'],
            'url': item['url']
        })

    return {
        'thumbnail': thumbnail_src,
        'title': title,
        'meta': meta,
        'description': description,
        'grouped': dict(grouped),
        'total_links': len(all_links)
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)