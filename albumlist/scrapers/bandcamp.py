import functools
import json
import lxml.html as lxh

import requests

from albumlist.scrapers import NotFoundError, links


def scrape_bandcamp_album_ids_from_attachments(message):
    for attachment in message['attachments']:
        try:
            if 'bandcamp.com' in attachment['from_url']:
                html = attachment['audio_html']
                html.replace('\\', '')
                _, seg = html.split('album=')
                yield seg[:seg.find('/')]
        except (ValueError, KeyError):
            continue


def scrape_bandcamp_album_ids_from_url(url, force=False):
    comment = '<!-- album id '
    comment_len = len(comment)
    if ('http' in url and 'bandcamp.com' in url) or force:
        url = url.replace('<', '').replace('>', '')
        url = url.replace('\\', '').split('|')[0]
        response = requests.get(url)
        if response.ok:
            content = response.text
            if comment in content:
                pos = content.find(comment)
                album_id = content[pos + comment_len:pos + comment_len + 20]
                return album_id.split('-->')[0].strip()
    raise NotFoundError


scrape_bandcamp_album_ids_from_url_forced = functools.partial(scrape_bandcamp_album_ids_from_url, force=True)


def scrape_bandcamp_album_cover_url_from_url(url):
    response = requests.get(url)
    if response.ok:
        html = lxh.fromstring(response.text)
        try:
            img = html.cssselect('div#tralbumArt')[0].cssselect('img')[0]
            return img.attrib['src']
        except (IndexError, KeyError):
            raise NotFoundError
    raise NotFoundError


def scrape_bandcamp_album_ids_from_artist_page(url):
    response = requests.get(url if url.endswith('/music') else f'{url}/music')
    if response.ok:
        html = lxh.fromstring(response.text)
        try:
            return [data.split('-')[1] for data in html.xpath('//@data-item-id') if data.startswith('album-')]
        except (IndexError, KeyError):
            raise NotFoundError
    raise NotFoundError


def scrape_bandcamp_tags_from_url(url):
    response = requests.get(url)
    if response.ok:
        html = lxh.fromstring(response.text)
        try:
            return [element.text for element in html.cssselect('a.tag')]
        except AttributeError:
            pass
    return []


def scrape_bandcamp_album_ids_from_messages(messages, do_requests=True):
    for message in messages:
        if message.get('type') == 'message':
            if 'attachments' in message:
                for album_id in scrape_bandcamp_album_ids_from_attachments(message):
                    yield str(album_id)
            elif do_requests:
                try:
                    for url in links.scrape_links_from_text(message['text']):
                        if 'bandcamp' in url:
                            yield str(scrape_bandcamp_album_ids_from_url(url))
                except (ValueError, KeyError, NotFoundError):
                    continue


def scrape_bandcamp_album_details_from_id(album_id):
    response = requests.get('https://bandcamp.com/EmbeddedPlayer/v=2/album=%s' % album_id)
    if response.ok:
        html = lxh.fromstring(response.text)
        try:
            data = json.loads(html.xpath('//@data-player-data')[0])
            return data['album_title'], data['artist'], data['linkback']
        except (KeyError, TypeError, ValueError):
            pass


def scrape_bandcamp_album_details_from_search(query):
    response = requests.get(f'https://bandcamp.com/search?q={query.replace(" ", "%20")}')
    if response.ok:
        html = lxh.fromstring(response.text)
        for album in html.cssselect('li.searchresult.album'):
            try:
                album_name = album.cssselect('.heading a')[0].text.strip()
                artist = album.cssselect('div.subhead')[0].text.strip()[3:]
                album_url = album.cssselect('.itemurl a')[0].text.strip()
                album_cover_url = album.cssselect('.art img')[0].attrib['src']
                yield album_name, artist, album_url, album_cover_url
            except (IndexError, KeyError):
                continue
    else:
        raise NotFoundError


def scrape_bandcamp_album_released_from_url(url):
    response = requests.get(url)
    if response.ok:
        html = lxh.fromstring(response.text)
        try:
            data = html.cssselect('div.tralbum-credits')[0].cssselect('meta')[0].attrib
            if data['itemprop'] == 'datePublished':
                return data['content']  # YYYYMMDD
        except (IndexError, KeyError):
            raise NotFoundError
    raise NotFoundError
