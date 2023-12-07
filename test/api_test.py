import os
from unittest import TestCase
from fastapi.testclient import TestClient

from test import INDEX_NAME, ELASTICSEARCH_URL
os.environ["eshosts"] = ELASTICSEARCH_URL
# make sure to set this env var before importing the app
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
                                     json={"q": "* AND publication_date:[2023-12-01 TO 2023-12-10]"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert 'total' in results
        assert results['total'] > 300
        assert results['total'] < 1000

    def test_paging(self):
        response = self._client.post(f'/v1/{INDEX_NAME}/search/result',
                                     json={"q": "*"}, timeout=TIMEOUT)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1000
        next_page_token = response.headers.get('x-resume-token')
        assert next_page_token is not None
