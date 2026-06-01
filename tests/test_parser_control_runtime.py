import pytest

import feapder.setting as setting
from feapder.core.parser_control import ParserControl
from feapder.network.request import Request
from feapder.network.item import Item


class FakeResponse:
    browser = None

    def __str__(self):
        return "<FakeResponse>"


class FakeParser:
    name = "FakeParser"

    def __init__(self):
        self.validated = []
        self.parsed = []

    def download_midware(self, request):
        return None

    def validate(self, request, response):
        self.validated.append((request, response))
        return True

    def parse(self, request, response):
        self.parsed.append((request, response))
        return [Item(title="ok")]

    def exception_request(self, request, response, e):
        return [request]

    def failed_request(self, request, response, e):
        return [request]


class FakeParserRecordingExceptions(FakeParser):
    def __init__(self):
        super().__init__()
        self.exception_requests = []

    def exception_request(self, request, response, e):
        self.exception_requests.append((request, response, e))
        return [request]


class FakeRequestBuffer:
    def __init__(self):
        self.requests = []
        self.deleted = []
        self.failed = []

    def put_request(self, request):
        self.requests.append(request)

    def put_del_request(self, request):
        self.deleted.append(request)

    def put_failed_request(self, request):
        self.failed.append(request)


class FakeItemBuffer:
    def __init__(self):
        self.items = []

    def put_item(self, item):
        self.items.append(item)


def build_control():
    control = object.__new__(ParserControl)
    control._parsers = []
    control._request_buffer = FakeRequestBuffer()
    control._item_buffer = FakeItemBuffer()
    return control


def test_find_parser_by_request_parser_name():
    parser = FakeParser()
    control = build_control()
    control._parsers = [parser]

    assert control._find_parser(Request(parser_name="FakeParser")) is parser


def test_find_parser_returns_none_for_missing_parser():
    control = build_control()
    control._parsers = [FakeParser()]

    assert control._find_parser(Request(parser_name="OtherParser")) is None


def test_run_callback_uses_named_callback():
    parser = FakeParser()
    parser.custom = lambda request, response: [Item(title="custom")]
    control = build_control()
    request = Request(callback="custom")
    response = FakeResponse()

    results = control._run_callback(parser, request, response)

    assert len(results) == 1
    assert results[0]["title"] == "custom"


def test_finish_request_prefers_item_buffer_for_item_results():
    control = build_control()

    control._finish_request(
        request_redis="raw-request",
        del_request_redis_after_item_to_db=True,
        del_request_redis_after_request_to_db=True,
    )

    assert control._item_buffer.items == ["raw-request"]
    assert control._request_buffer.deleted == []


def test_finish_request_deletes_via_request_buffer_for_request_results():
    control = build_control()

    control._finish_request(
        request_redis="raw-request",
        del_request_redis_after_item_to_db=False,
        del_request_redis_after_request_to_db=True,
    )

    assert control._item_buffer.items == []
    assert control._request_buffer.deleted == ["raw-request"]


def test_finish_request_deletes_unclaimed_request_by_default():
    control = build_control()

    control._finish_request(
        request_redis="raw-request",
        del_request_redis_after_item_to_db=False,
        del_request_redis_after_request_to_db=False,
    )

    assert control._request_buffer.deleted == ["raw-request"]


def test_deal_request_uses_request_returned_by_download_middleware(monkeypatch):
    parser = FakeParser()
    control = build_control()
    control._parsers = [parser]
    response = FakeResponse()
    replacement_request = Request(
        "https://replacement.example.com",
        parser_name="FakeParser",
        auto_request=True,
    )

    def replace_request(request):
        return replacement_request, response

    request = Request(
        "https://example.com",
        parser_name="FakeParser",
        download_midware=replace_request,
    )

    monkeypatch.setattr(control, "record_download_status", lambda status, spider: None)
    monkeypatch.setattr(control, "_sleep_after_request", lambda: None)

    control.deal_request({"request_obj": request, "request_redis": "raw-request"})

    assert parser.validated == [(replacement_request, response)]
    assert parser.parsed == [(replacement_request, response)]


def test_deal_request_handles_fetch_exception_on_replacement_request(monkeypatch):
    parser = FakeParserRecordingExceptions()
    control = build_control()
    control._parsers = [parser]
    replacement_request = Request(
        "https://replacement.example.com",
        parser_name="FakeParser",
        auto_request=True,
    )

    def raise_fetch_error():
        raise RuntimeError("replacement fetch failed")

    replacement_request.get_response = raise_fetch_error

    def replace_request(request):
        return replacement_request

    request = Request(
        "https://example.com",
        parser_name="FakeParser",
        download_midware=replace_request,
    )

    monkeypatch.setattr(control, "record_download_status", lambda status, spider: None)
    monkeypatch.setattr(control, "_sleep_after_request", lambda: None)
    monkeypatch.setattr(setting, "LOG_LEVEL", "INFO")

    control.deal_request({"request_obj": request, "request_redis": None})

    assert parser.exception_requests
    assert parser.exception_requests[0][0] is replacement_request


def test_deal_request_dispatches_item_and_marks_request_for_item_delete(monkeypatch):
    parser = FakeParser()
    control = build_control()
    control._parsers = [parser]
    response = FakeResponse()
    request = Request(
        "https://example.com",
        parser_name="FakeParser",
        auto_request=False,
    )

    monkeypatch.setattr(control, "record_download_status", lambda status, spider: None)
    monkeypatch.setattr(control, "_sleep_after_request", lambda: None)

    control.deal_request({"request_obj": request, "request_redis": "raw-request"})

    assert len(control._item_buffer.items) == 2
    assert isinstance(control._item_buffer.items[0], Item)
    assert control._item_buffer.items[1] == "raw-request"
    assert control._request_buffer.deleted == []
