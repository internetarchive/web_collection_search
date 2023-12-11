import os
from unittest import TestCase
import datetime as dt
from fastapi.testclient import TestClient

from test import INDEX_NAME, ELASTICSEARCH_URL
# make sure to set these env vars before importing the app so it runs against a test ES you've set up with
# the `create_fixtures.py` script
os.environ["INDEXES"] = INDEX_NAME
os.environ["ESHOSTS"] = ELASTICSEARCH_URL
os.environ["ELASTICSEARCH_INDEX_NAME_PREFIX"] = "mediacloud"
from api import app

TIMEOUT = 30


class ApiTest(TestCase):

    def setUp(self):
        self._client = TestClient(app)

    def test_overview_all(self):
        # make sure all stories come back and domain is right
        response = self._client.post(f'/v1/{INDEX_NAME}/search/overview', json={"q": "*"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert 'total' in results
        assert results['total'] > 1000
        assert 'matches' in results
        for story in results['matches']:
            assert 'canonical_domain' in story
            assert story['canonical_domain'] == 'example.com'

    def test_overview_no_results(self):
        response = self._client.post(f'/v1/{INDEX_NAME}/search/overview', json={"q": "asdfdf"}, timeout=TIMEOUT)
        assert response.status_code == 404

    def test_overview_by_content(self):
        response = self._client.post(f'/v1/{INDEX_NAME}/search/overview', json={"q": "article"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert 'total' in results
        assert results['total'] > 1000
        response = self._client.post(f'/v1/{INDEX_NAME}/search/overview', json={"q": "1"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert 'total' in results
        assert results['total'] < 1000

    def test_overview_by_pub_date(self):
        response = self._client.post(f'/v1/{INDEX_NAME}/search/overview',
                                     json={"q": "* AND publication_date:[2023-11-01 TO 2023-12-10]"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert 'total' in results
        assert results['total'] > 300
        assert results['total'] < 1200

    def test_paging(self):
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1000
        next_page_token = response.headers.get('x-resume-token')
        assert next_page_token is not None

    def test_text_content_expanded(self):
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "expanded": 1}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1000
        for story in results:
            assert 'text_content' in story
            assert len(story['text_content']) > 0

    def test_story_sort_order(self):
        # desc
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        last_pub_date = tomorrow
        for story in results:
            assert 'text_content' not in story
            assert 'publication_date' in story
            story_pub_date = dt.date.fromisoformat(story['publication_date'])
            assert story_pub_date <= last_pub_date
            last_pub_date = story_pub_date
        # asc
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "sort_order": "asc"}, timeout=TIMEOUT)
        results = response.json()
        a_long_time_ago = dt.date(2000, 1, 1)
        last_pub_date = a_long_time_ago
        for story in results:
            assert 'publication_date' in story
            story_pub_date = dt.date.fromisoformat(story['publication_date'])
            assert story_pub_date >= last_pub_date
            last_pub_date = story_pub_date
        # invalid
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "sort_order": "foo"}, timeout=TIMEOUT)
        assert response.status_code == 400

    def test_story_sort_field(self):
        # desc
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "sort_field": "publication_date"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        last_date = tomorrow
        for story in results:
            assert 'text_content' not in story
            assert 'publication_date' in story
            story_date = dt.date.fromisoformat(story['publication_date'])
            assert story_date <= last_date
            last_date = story_date
        # indexed date
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "sort_field": "indexed_date"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        last_date = tomorrow
        for story in results:
            assert 'indexed_date' in story
            story_date = dt.date.fromisoformat(story['indexed_date'])
            assert story_date <= last_date
            last_date = story_date
        # invalid
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "sort_field": "imagined_date"}, timeout=TIMEOUT)
        assert response.status_code == 400

    def test_page_size(self):
        # test valid number
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "page_size": 103}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 103
        # test invalid value
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "page_size": '💩'}, timeout=TIMEOUT)
        assert response.status_code == 422
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*", "page_size": -10}, timeout=TIMEOUT)
        assert response.status_code == 400
