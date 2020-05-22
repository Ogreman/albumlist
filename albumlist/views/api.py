import csv
import flask
import io
import itertools

from albumlist import constants
from albumlist.delayed import queued
from albumlist.models import DatabaseError
from albumlist.models import albums as albums_model, list as list_model
from albumlist.scrapers import bandcamp, links


api_blueprint = flask.Blueprint(name='api',
                                import_name=__name__,
                                url_prefix='/api')


@api_blueprint.after_request
def after_request(response):
    if hasattr(response, 'headers'):
        response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@api_blueprint.route('/list', methods=['GET'])
def api_list_albums():
    try:
        return flask.jsonify(list_model.get_list()), 200
    except DatabaseError as e:
        print('[db]: failed to get list')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/list/count', methods=['GET'])
def api_id_count():
    try:
        return flask.jsonify({'count': list_model.get_list_count()}), 200
    except DatabaseError as e:
        print('[db]: failed to get list count')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/albums', methods=['GET'])
def api_list_album_details():
    channel = flask.request.args.get('channel')
    if channel:
        albums = albums_model.get_albums_by_channel_with_tags(channel)
        key = f'api-albums-{channel}'
    else:
        albums = albums_model.get_albums_with_tags()
        key = 'api-albums'
    try:
        details = flask.current_app.cache.get(key)
        if not details:
            details = albums_model.Album.details_map_from_albums(albums)
            details = [{key: d} for key, d in details.items()]
            flask.current_app.cache.set(key, details, 60 * 5)
        return flask.jsonify(details), 200
    except DatabaseError as e:
        print('[db]: failed to get albums')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/albums/count', methods=['GET'])
def api_count_albums():
    try:
        return flask.jsonify({'count': albums_model.get_albums_count()}), 200
    except DatabaseError as e:
        print('[db]: failed to get albums count')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/albums/dump', methods=['GET'])
def api_dump_album_details():
    # need StringIO for csv.writer
    proxy = io.StringIO()
    albums = albums_model.get_albums_with_users()
    first_album = next(albums)
    csv_writer = csv.DictWriter(proxy, fieldnames=first_album.fieldnames)
    csv_writer.writeheader()
    for album in itertools.chain([first_album], albums):
        csv_writer.writerow(album.to_dict())
    # and BytesIO for flask.send_file
    mem = io.BytesIO()
    mem.write(proxy.getvalue().encode('utf-8'))
    mem.seek(0)
    proxy.close()
    # see: https://stackoverflow.com/a/45111660
    return flask.send_file(mem,
                           as_attachment=True,
                           attachment_filename="albums.csv",
                           mimetype='text/csv',
                           cache_timeout=0 if flask.request.args.get('fresh') else None)


@api_blueprint.route('/album/<album_id>', methods=['GET'])
def api_album(album_id):
    try:
        if flask.request.args.get('reviews'):
            album = albums_model.get_album_details_with_reviews(album_id)
        else:
            album = flask.current_app.get_cached_album_details(album_id)
        if album is None:
            return flask.jsonify({'text': 'not found'}), 404
        response = {
            'text': 'success',
            'album': album.to_dict(),
        }
        return flask.jsonify(response), 200
    except DatabaseError as e:
        print(f'[db]: failed to get album: {album_id}')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/album/<album_id>/reviews', methods=['GET'])
def api_album_reviews(album_id):
    try:
        album = albums_model.get_album_details_with_reviews(album_id)
        if album is None:
            return flask.jsonify({'text': 'not found'}), 404
        response = {
            'text': 'success',
            'reviews': album.reviews,
        }
        return flask.jsonify(response), 200
    except DatabaseError as e:
        print(f'[db]: failed to get album: {album_id}')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/tags/<tag>', methods=['GET'])
def api_album_by_tag(tag):
    key = f'api-tags-{tag}'
    try:
        details = flask.current_app.cache.get(key)
        if not details:
            albums = albums_model.get_albums_by_tag(tag)
            details = albums_model.Album.details_map_from_albums(albums)
            details = [{key: d} for key, d in details.items()]
            flask.current_app.cache.set(key, details, 60 * 30)
        return flask.jsonify(details), 200
    except DatabaseError as e:
        print(f'[db]: failed to get tag: {tag}')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/bc/<album_id>', methods=['GET'])
def api_bc(album_id):
    return flask.redirect(constants.BANDCAMP_URL_TEMPLATE.format(album_id=album_id), code=302)


@api_blueprint.route('/albums/random', methods=['GET'])
def api_random():
    try:
        album = albums_model.get_random_album()
        if album is None:
            return flask.jsonify({'text': 'not found'}), 404
        response = {
            'text': 'success',
            'album': album.to_dict(),
        }
        return flask.jsonify(response), 200
    except DatabaseError as e:
        print(f'[db]: failed to get random album')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/albums/available/urls', methods=['GET'])
def available_urls():
    try:
        key = 'api-albums-available-urls'
        urls = flask.current_app.cache.get(key)
        if not urls:
            urls = [album.album_url for album in albums_model.get_albums_available()]
            flask.current_app.cache.set(key, urls, 60 * 30)
        return flask.jsonify(urls), 200
    except DatabaseError as e:
        print('[db]: failed to get album urls')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/albums/unavailable/count', methods=['GET'])
def unavailable_count():
    try:
        return flask.jsonify({'count': albums_model.get_albums_unavailable_count()}), 200
    except DatabaseError as e:
        print('[db]: failed to get unavailable albums count')
        print(f'[db]: {e}')
        return flask.jsonify({'text': 'failed'}), 500


@api_blueprint.route('/albums/scrape', methods=['POST'])
def scrape_album():
    form_data = flask.request.form
    for url in links.scrape_links_from_text(form_data.get('url', '')):
        flask.current_app.logger.info(f'[api]: scraping {url}...')
        queued.deferred_consume.delay(
            url,
            bandcamp.scrape_bandcamp_album_ids_from_url_forced,
            list_model.add_to_list,
        )
    return 'OK', 200


@api_blueprint.route('', methods=['GET'])
def all_endpoints():
    rules = [ 
        (list(rule.methods), rule.rule) 
        for rule in flask.current_app.url_map.iter_rules() 
        if rule.endpoint.startswith('api')
    ]
    return flask.jsonify({'api': rules}), 200
