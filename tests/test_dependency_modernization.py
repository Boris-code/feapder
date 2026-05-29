import inspect

from feapder.db.redisdb import RedisDB
from feapder.utils.webdriver.selenium_driver import SeleniumDriver


class OldStyleService:
    def __init__(
        self, executable_path=None, port=0, service_args=None, log_path=None, **kwargs
    ):
        self.executable_path = executable_path
        self.port = port
        self.service_args = service_args
        self.log_path = log_path


class NewStyleService:
    def __init__(
        self, executable_path=None, port=0, service_args=None, log_output=None, **kwargs
    ):
        self.executable_path = executable_path
        self.port = port
        self.service_args = service_args
        self.log_output = log_output


class FakeBrowser:
    def set_window_size(self, *args):
        self.window_size = args


def make_selenium_driver(**kwargs):
    driver = object.__new__(SeleniumDriver)
    driver._kwargs = kwargs
    driver._executable_path = kwargs.pop("executable_path", "/tmp/driver")
    driver._auto_install_driver = False
    driver._proxy = None
    driver._user_agent = None
    driver._load_images = True
    driver._headless = False
    driver._custom_argument = None
    driver._window_size = None
    return driver


def test_selenium_service_log_path_supports_old_and_new_service_api():
    driver = make_selenium_driver(
        service_log_path="/tmp/webdriver.log", service_args=["--verbose"], port=1234
    )

    old_service = driver.build_service(OldStyleService)
    new_service = driver.build_service(NewStyleService)

    assert old_service.executable_path == "/tmp/driver"
    assert old_service.service_args == ["--verbose"]
    assert old_service.port == 1234
    assert old_service.log_path == "/tmp/webdriver.log"
    assert new_service.executable_path == "/tmp/driver"
    assert new_service.service_args == ["--verbose"]
    assert new_service.port == 1234
    assert new_service.log_output == "/tmp/webdriver.log"


def test_selenium_firefox_binary_maps_to_options_binary_location():
    driver = make_selenium_driver(firefox_binary="/tmp/firefox")
    captured = {}

    def create_driver(driver_cls, options, service):
        captured["options"] = options
        captured["service"] = service
        return FakeBrowser()

    driver.create_driver = create_driver
    driver.build_service = lambda *args, **kwargs: None

    assert driver.firefox_driver() is not None
    assert captured["options"].binary_location == "/tmp/firefox"
    assert captured["service"] is None


def test_selenium_driver_kwargs_keep_public_constructor_args_internal():
    driver = make_selenium_driver(
        keep_alive=False,
        executable_path="/tmp/driver",
        desired_capabilities={"acceptInsecureCerts": True},
        service_args=["--verbose"],
    )

    assert driver.get_driver_kwargs() == {"keep_alive": False}


def test_redisdb_public_api_signatures_are_preserved():
    expected = {
        "__init__": [
            "self",
            "ip_ports",
            "db",
            "user_pass",
            "url",
            "decode_responses",
            "service_name",
            "max_connections",
            "kwargs",
        ],
        "from_url": ["url"],
        "zadd": ["self", "table", "values", "prioritys"],
        "zget": ["self", "table", "count", "is_pop"],
        "zexists": ["self", "table", "values"],
        "setbit": ["self", "table", "offsets", "values"],
        "getbit": ["self", "table", "offsets"],
    }

    for method_name, parameters in expected.items():
        signature = inspect.signature(getattr(RedisDB, method_name))
        assert list(signature.parameters) == parameters
