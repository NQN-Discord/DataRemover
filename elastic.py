from typing import AsyncGenerator
from logging import getLogger

from elasticsearch_async import AsyncElasticsearch
from elasticsearch_py_async_bulk import bulk

log = getLogger(__name__)


class ElasticSearchClient:
    def __init__(self, hosts):
        self.hosts = hosts
        self._db = None
        self._alive = 0
        self._has_waited = False

    async def __aenter__(self):
        if self._alive == 0:
            _db = _ElasticSearchDB(self.hosts)
            if not self._has_waited:
                await _db._client.cluster.health(wait_for_status='yellow')
                self._has_waited = True
            self._db = _db
        self._alive += 1
        return self._db

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._alive -= 1
        if self._alive == 0:
            await self._db.close()
        return False


class _ElasticSearchDB:
    def __init__(self, hosts):
        self._client = AsyncElasticsearch(hosts=hosts, maxsize=40)

    async def close(self):
        await self._client.transport.close()

    async def _scroll(self, body, index, **kwargs):
        resp = await self._client.search(
            body=body,
            index=index,
            scroll="1m",
            **kwargs
        )
        scroll_id = resp.get('_scroll_id')
        try:
            first_run = True
            while True:
                # if we didn't set search_type to scan initial search contains data
                if first_run:
                    first_run = False
                else:
                    resp = await self._client.scroll(scroll_id, scroll="1m")

                for hit in resp['hits']['hits']:
                    yield hit

                scroll_id = resp.get('_scroll_id')
                # end of scroll
                if scroll_id is None or not resp['hits']['hits']:
                    break
        finally:
            if scroll_id:
                await self._client.clear_scroll(body={'scroll_id': [scroll_id]}, ignore=(404, ))

    async def bulk_delete(self, index: str, ids: AsyncGenerator, chunk_size: int = 10000):
        await bulk(
            self._client,
            ({
                "_op_type": "delete",
                "_index": index,
                "_type": "_doc",
                "_id": id
            } for id in ids),
            chunk_size=chunk_size,
            doc_type="_doc"
        )