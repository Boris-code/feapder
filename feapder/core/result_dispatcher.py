# -*- coding: utf-8 -*-
"""
Parser result routing for runtime parser controls.
"""
from collections.abc import Iterable
from dataclasses import dataclass

from feapder.network.item import Item
from feapder.network.request import Request


@dataclass
class DispatchResult:
    del_request_redis_after_item_to_db: bool = False
    del_request_redis_after_request_to_db: bool = False


class ResultDispatcher:
    REQUEST_RESULT = 1
    ITEM_RESULT = 2

    def __init__(
        self,
        *,
        request_buffer,
        item_buffer,
        deal_request,
        sync_request_factory=None,
        allow_callable=True,
    ):
        self._request_buffer = request_buffer
        self._item_buffer = item_buffer
        self._deal_request = deal_request
        self._sync_request_factory = sync_request_factory or (lambda request: request)
        self._allow_callable = allow_callable

    def dispatch(self, parser, request, results):
        if results and not isinstance(results, Iterable):
            raise Exception(
                "%s.%s返回值必须可迭代" % (parser.name, request.callback or "parse")
            )

        dispatch_result = DispatchResult()
        result_type = 0

        for result in results or []:
            if isinstance(result, Request):
                result_type = self.REQUEST_RESULT
                result.parser_name = result.parser_name or parser.name
                if result.request_sync:
                    self._deal_request(self._sync_request_factory(result))
                else:
                    self._request_buffer.put_request(result)
                    dispatch_result.del_request_redis_after_request_to_db = True

            elif isinstance(result, Item):
                result_type = self.ITEM_RESULT
                self._item_buffer.put_item(result)
                dispatch_result.del_request_redis_after_item_to_db = True

            elif callable(result) and self._allow_callable:
                if result_type == self.ITEM_RESULT:
                    self._item_buffer.put_item(result)
                    dispatch_result.del_request_redis_after_item_to_db = True
                else:
                    self._request_buffer.put_request(result)
                    dispatch_result.del_request_redis_after_request_to_db = True

            elif result is not None:
                raise TypeError(self._format_type_error(parser, request, result))

        return dispatch_result

    def _format_type_error(self, parser, request, result):
        callback_name = (
            request.callback
            and callable(request.callback)
            and getattr(request.callback, "__name__")
            or request.callback
        ) or "parse"
        expected = "Request、Item or callback" if self._allow_callable else "Request or Item"
        return (
            f"{parser.name}.{callback_name} result expect {expected}, "
            f"bug get type: {type(result)}"
        )
