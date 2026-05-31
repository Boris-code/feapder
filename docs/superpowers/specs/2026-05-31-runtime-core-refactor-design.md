# Core Runtime Refactor Design

Date: 2026-05-31

## Scope

This refactor focuses on the runtime path that moves work through feapder:

- `Scheduler`
- `Collector`
- `ParserControl`
- `RequestBuffer`
- `ItemBuffer`

The first implementation phase keeps the public spider APIs compatible. It does not change how users subclass `AirSpider`, `Spider`, `TaskSpider`, or `BatchSpider`, and it does not redesign their inheritance yet. The spider inheritance cleanup remains a follow-up phase after the runtime path is safer and better covered by tests.

## Current Problems

The runtime path works, but several responsibilities are tangled:

- Thread lifecycle state is duplicated. Multiple classes maintain `_thread_stop`, `_is_adding_to_db`, `is_show_tip`, queue checks, and direct `_started.clear()` calls in slightly different ways.
- `ParserControl.deal_request` is too large. It handles parser lookup, download middleware, response fetching, validation, callback execution, result routing, retry, failed request persistence, metrics, browser release, and request deletion in one method.
- `ParserControl` and `AirSpiderParserControl` duplicate most request handling logic while differing mainly in queue backend and completion semantics.
- `Scheduler.all_thread_is_done()` depends on implementation details from collector and buffers. This makes shutdown sensitive to timing and temporary state.
- `RequestBuffer` and `ItemBuffer` both combine queueing, flushing, retry callbacks, persistence, and thread control. Their idle states are not explicit enough for a scheduler to reason about safely.
- Result handling rules are repeated in several places. A yielded value can be `Request`, `Item`, `UpdateItem`, callable, or invalid, but the classification logic is not centralized.
- Data safety concerns such as `eval`-based deserialization exist in adjacent runtime code. Replacing serialization is valuable, but it is not part of the first implementation slice unless touched code needs a small compatibility wrapper.

## Goals

1. Make runtime thread state explicit and consistent.
2. Split request processing into small units with clear responsibilities.
3. Reduce duplication between Redis-backed and in-memory parser control paths.
4. Make scheduler shutdown decisions depend on a small runtime status interface instead of scattered implementation details.
5. Preserve existing user-facing behavior, settings, Redis key formats, retry semantics, and callback semantics.
6. Add lightweight tests that do not require Redis, MySQL, browsers, or network access.

## Non-Goals

- Do not change the public constructor signatures of `Scheduler`, `AirSpider`, `Spider`, `TaskSpider`, or `BatchSpider`.
- Do not rewrite the storage format for requests, responses, failed items, or failed requests in this phase.
- Do not require Redis or MySQL for the new unit tests.
- Do not remove existing settings or documented behavior.
- Do not perform the spider inheritance refactor in this phase.

## Proposed Architecture

### Runtime Worker State

Introduce a small shared lifecycle helper for runtime threads. The helper should expose:

- `request_stop()`
- `is_stop_requested`
- `mark_busy()`
- `mark_idle()`
- `is_idle`

`Collector`, `ParserControl`, `RequestBuffer`, and `ItemBuffer` can keep inheriting from `threading.Thread`, but their public state checks should move toward explicit methods:

- `is_idle()`
- `pending_count()`
- `is_stopped()` where useful

This allows `Scheduler` to ask each component for status instead of reading several unrelated flags and queues.

### Runtime Status Interface

Add a small internal status contract used by `Scheduler.all_thread_is_done()`:

- Collector is done when it is idle and has no pending local or backend requests.
- Parser controls are done when each worker is idle.
- Request buffer is done when it has no queued writes, no queued deletions, and is not flushing.
- Item buffer is done when it has no queued items and is not flushing.

The scheduler should keep the current three-pass stability check, but delegate each component check to the component itself.

### Parser Request Processing

Split `ParserControl.deal_request` into private units:

- `_find_parser(request)`
- `_prepare_response(parser, request)`
- `_run_callback(parser, request, response)`
- `_dispatch_results(parser, request, results, request_redis)`
- `_handle_exception(parser, request, response, error, request_redis, used_download_midware)`
- `_finish_request(request_redis, finish_action)`
- `_sleep_after_request()`

The method `deal_request` remains as the public entry point for compatibility, but becomes orchestration code. This makes retry and success paths easier to test independently.

### Result Dispatcher

Introduce an internal result dispatcher for `Request`, `Item`, and callable values. It should encode the current behavior:

- `Request` values receive a default `parser_name`.
- Synchronous requests are processed immediately.
- Asynchronous requests go to `RequestBuffer`.
- `Item` and `UpdateItem` values go to `ItemBuffer`.
- Callable values follow the current "previous result type" rule: after an item they are item callbacks; otherwise they are request callbacks.
- Invalid non-`None` values raise `TypeError` with the parser and callback name.

For the first phase, wire this dispatcher into `ParserControl`. Later phases can reuse it from `Scheduler`, `Spider`, `TaskSpider`, and `BatchSpider`.

### ParserControl Variants

Keep both `ParserControl` and `AirSpiderParserControl` classes for compatibility, but move shared behavior into a base implementation. The variants should differ only in:

- How they receive work.
- How they mark a request complete.
- Whether failed requests are persisted to Redis.

This avoids changing `AirSpider` behavior while removing duplicated parsing, retry, middleware, and result handling logic.

### Buffer Semantics

`RequestBuffer` should make these states explicit:

- queued new requests
- queued deletion requests
- currently flushing

`ItemBuffer` should make these states explicit:

- queued items or callbacks
- currently flushing
- export retry counters

Both buffers should keep `flush()` as a synchronous method. Their thread loop continues calling `flush()` periodically. `stop()` should request shutdown, and the scheduler should still call explicit flushing before treating the runtime as complete.

### Error Handling

The refactor must preserve current error behavior:

- Request download exceptions continue to increment download exception metrics.
- Parser exceptions continue to increment parser exception metrics.
- Proxy deletion behavior remains based on `PROXY_MAX_FAILED_TIMES`.
- `exception_request` and `failed_request` compatibility hooks remain intact.
- Browser instances are returned to the render downloader in a `finally` block.
- The original request is preserved when download middleware mutates a request and a retry or failed-request persistence is needed.

Error handling should become easier to read by returning a small internal result from `_handle_exception`, such as whether to delete the active Redis request via the request buffer or via the item buffer.

## Data Flow

1. `Scheduler` starts buffers, collector, parser workers, retry handlers, and optional start request distribution.
2. `Collector` atomically reserves ready Redis requests and exposes them through its local queue.
3. `ParserControl` obtains one request, marks itself busy, finds the parser, downloads or reuses a response, validates it, runs the callback, and dispatches yielded results.
4. `RequestBuffer` persists new requests and deletion markers.
5. `ItemBuffer` persists items and deletes completed Redis requests after item persistence succeeds.
6. `Scheduler` polls component status. It ends the spider only after all components report stable idle status.

For `AirSpider`, the same parser-processing flow applies, but the request source is `MemoryDB` and request completion does not use Redis deletion markers.

## Compatibility Strategy

- Keep class names and imports stable.
- Keep public method names such as `deal_request`, `flush`, `stop`, `is_not_task`, `get_requests_count`, and `is_adding_to_db`.
- Add new internal methods instead of removing old methods immediately.
- Preserve existing Redis key names and serialized values.
- Preserve callback ordering and the current callable routing rule.
- Preserve warning, logging, and metric names unless a test proves an existing message is wrong.

## Testing Strategy

Add focused unit tests around the new internal boundaries:

- Collector idle and pending status with a fake RedisDB.
- RequestBuffer status before enqueue, during flush, and after flush with a fake DB.
- ItemBuffer status before enqueue, during flush, and after successful fake pipeline export.
- ParserControl result dispatch for `Request`, synchronous `Request`, `Item`, callback, and invalid result.
- ParserControl retry behavior for a controlled exception without network access.
- Scheduler completion check using fake components that transition from busy to idle.

Existing integration tests can remain as broader coverage. This phase should not require Redis, MySQL, Playwright, Selenium, or live HTTP.

## Implementation Phases

### Phase 1: Status Surfaces

Add explicit idle and pending methods to collector and buffers. Update `Scheduler.all_thread_is_done()` to use these methods while preserving the three-pass stability check.

### Phase 2: ParserControl Extraction

Split `ParserControl.deal_request` into smaller private methods without changing behavior. Add tests for the extracted methods using fake parsers, fake buffers, and fake requests.

### Phase 3: Shared Parser Runtime

Move duplicated logic from `ParserControl` and `AirSpiderParserControl` into shared helpers or a shared base class. Keep the concrete classes as compatibility wrappers.

### Phase 4: Runtime Result Dispatcher

Introduce the internal dispatcher and wire it into parser controls. Keep legacy result behavior intact.

### Phase 5: Buffer Stop and Flush Hardening

Make stop behavior explicit. Ensure a stopped buffer can report pending work accurately and that final flushes are deterministic.

## Acceptance Criteria

- Public spider examples in the docs continue to run with the same API.
- `Scheduler.all_thread_is_done()` no longer reads buffer and parser internals directly when an explicit status method exists.
- `ParserControl.deal_request` is substantially shorter and delegates download, callback, dispatch, exception, and completion responsibilities.
- `ParserControl` and `AirSpiderParserControl` share request-processing behavior instead of duplicating it.
- New lightweight tests cover the status and dispatch behavior without external services.
- Existing compatible tests still pass in the available local environment.

## Follow-Up Work

After this runtime refactor, a separate design should address the spider type hierarchy. The likely direction is a shared `BaseSpider` plus a distributed branch:

- `BaseSpider -> AirSpider`
- `BaseSpider -> Spider -> TaskSpider -> BatchSpider`

That work should wait until the runtime path has clearer component boundaries and tests, because changing inheritance before stabilizing runtime behavior would make regressions harder to isolate.
