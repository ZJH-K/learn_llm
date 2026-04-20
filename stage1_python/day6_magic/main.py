from solution import Config


DATA = {
    "app": "demo",
    "version": 1,
    "database": {
        "host": "localhost",
        "port": 5432,
    },
}


def run_basic():
    print("=== 基础点取 ===")
    cfg = Config(DATA)
    print(cfg.app)
    print(cfg.version)


def run_nested():
    print("\n=== 嵌套点取 ===")
    cfg = Config(DATA)
    print(cfg.database.host)
    print(cfg.database.port)


def run_repr():
    print("\n=== __repr__ ===")
    cfg = Config(DATA)
    print(cfg)


def run_eq():
    print("\n=== __eq__ ===")
    print(Config({"a": 1, "b": 2}) == Config({"a": 1, "b": 2}))
    print(Config({"a": 1}) == Config({"a": 2}))
    print(Config({"a": 1}) == {"a": 1})


def run_missing():
    print("\n=== AttributeError ===")
    cfg = Config(DATA)
    try:
        cfg.nonexistent
    except AttributeError as e:
        print(f"caught: {e}")


if __name__ == "__main__":
    run_basic()
    run_nested()
    run_repr()
    run_eq()
    run_missing()
