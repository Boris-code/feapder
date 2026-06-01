import pytest

from feapder.core.result_dispatcher import ResultDispatcher
from feapder.network.item import Item, UpdateItem
from feapder.network.request import Request


class FakeParser:
    name = "FakeParser"


class FakeRequestBuffer:
    def __init__(self):
        self.requests = []

    def put_request(self, request):
        self.requests.append(request)


class FakeItemBuffer:
    def __init__(self):
        self.items = []

    def put_item(self, item):
        self.items.append(item)


def test_dispatcher_routes_async_request_and_sets_parser_name():
    request_buffer = FakeRequestBuffer()
    item_buffer = FakeItemBuffer()
    calls = []
    dispatcher = ResultDispatcher(
        request_buffer=request_buffer,
        item_buffer=item_buffer,
        deal_request=calls.append,
        sync_request_factory=lambda request: {"request_obj": request, "request_redis": None},
    )
    next_request = Request("https://example.com")

    result = dispatcher.dispatch(
        parser=FakeParser(),
        request=Request("https://root.example.com", callback="parse"),
        results=[next_request],
    )

    assert next_request.parser_name == "FakeParser"
    assert request_buffer.requests == [next_request]
    assert item_buffer.items == []
    assert calls == []
    assert result.del_request_redis_after_request_to_db is True
    assert result.del_request_redis_after_item_to_db is False


def test_dispatcher_routes_sync_request_to_deal_request():
    request_buffer = FakeRequestBuffer()
    item_buffer = FakeItemBuffer()
    calls = []
    dispatcher = ResultDispatcher(
        request_buffer=request_buffer,
        item_buffer=item_buffer,
        deal_request=calls.append,
        sync_request_factory=lambda request: {"request_obj": request, "request_redis": None},
    )
    next_request = Request("https://example.com", request_sync=True)

    result = dispatcher.dispatch(
        parser=FakeParser(),
        request=Request("https://root.example.com"),
        results=[next_request],
    )

    assert calls == [{"request_obj": next_request, "request_redis": None}]
    assert request_buffer.requests == []
    assert result.del_request_redis_after_request_to_db is False


def test_dispatcher_routes_item_and_update_item_to_item_buffer():
    request_buffer = FakeRequestBuffer()
    item_buffer = FakeItemBuffer()
    dispatcher = ResultDispatcher(
        request_buffer=request_buffer,
        item_buffer=item_buffer,
        deal_request=lambda request: None,
    )
    item = Item(title="one")
    update_item = UpdateItem(id=1, title="two")

    result = dispatcher.dispatch(
        parser=FakeParser(),
        request=Request("https://root.example.com"),
        results=[item, update_item],
    )

    assert item_buffer.items == [item, update_item]
    assert request_buffer.requests == []
    assert result.del_request_redis_after_item_to_db is True


def test_dispatcher_routes_callable_after_item_to_item_buffer():
    request_buffer = FakeRequestBuffer()
    item_buffer = FakeItemBuffer()
    dispatcher = ResultDispatcher(
        request_buffer=request_buffer,
        item_buffer=item_buffer,
        deal_request=lambda request: None,
    )
    callback = lambda: None

    result = dispatcher.dispatch(
        parser=FakeParser(),
        request=Request("https://root.example.com"),
        results=[Item(title="one"), callback],
    )

    assert item_buffer.items[-1] is callback
    assert request_buffer.requests == []
    assert result.del_request_redis_after_item_to_db is True


def test_dispatcher_routes_callable_without_prior_item_to_request_buffer():
    request_buffer = FakeRequestBuffer()
    item_buffer = FakeItemBuffer()
    dispatcher = ResultDispatcher(
        request_buffer=request_buffer,
        item_buffer=item_buffer,
        deal_request=lambda request: None,
    )
    callback = lambda: None

    result = dispatcher.dispatch(
        parser=FakeParser(),
        request=Request("https://root.example.com"),
        results=[callback],
    )

    assert request_buffer.requests == [callback]
    assert item_buffer.items == []
    assert result.del_request_redis_after_request_to_db is True


def test_dispatcher_rejects_callable_when_disabled():
    dispatcher = ResultDispatcher(
        request_buffer=FakeRequestBuffer(),
        item_buffer=FakeItemBuffer(),
        deal_request=lambda request: None,
        allow_callable=False,
    )

    with pytest.raises(TypeError, match="FakeParser.parse result expect Request or Item"):
        dispatcher.dispatch(
            parser=FakeParser(),
            request=Request("https://root.example.com"),
            results=[lambda: None],
        )


def test_dispatcher_rejects_invalid_result_type():
    dispatcher = ResultDispatcher(
        request_buffer=FakeRequestBuffer(),
        item_buffer=FakeItemBuffer(),
        deal_request=lambda request: None,
    )

    with pytest.raises(TypeError, match="FakeParser.parse result expect Request"):
        dispatcher.dispatch(
            parser=FakeParser(),
            request=Request("https://root.example.com"),
            results=[object()],
        )
