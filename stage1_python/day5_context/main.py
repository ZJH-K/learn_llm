"""验收脚本:跑这个文件,两部分输出都对才算作业通过。

期望输出(严格):

=== class 版 · 正常路径 ===
[DB] connect to orders
[DB] exec: INSERT ...
[DB] exec: UPDATE ...
[DB] commit (2 statements)
[DB] close

=== class 版 · 异常路径 ===
[DB] connect to orders
[DB] exec: DELETE ...
[DB] rollback (1 statements discarded)
[DB] close
caught: oops

=== generator 版 · 正常路径 ===
[DB] connect to users
[DB] exec: SELECT ...
[DB] commit (1 statements)
[DB] close

=== generator 版 · 异常路径 ===
[DB] connect to users
[DB] exec: INSERT ...
[DB] rollback (1 statements discarded)
[DB] close
caught: boom
"""

from solution import DBConnection, db_connection


def run_class_happy():
    print("=== class 版 · 正常路径 ===")
    with DBConnection("orders") as conn:
        conn.execute("INSERT ...")
        conn.execute("UPDATE ...")


def run_class_error():
    print("\n=== class 版 · 异常路径 ===")
    try:
        with DBConnection("orders") as conn:
            conn.execute("DELETE ...")
            raise RuntimeError("oops")
    except RuntimeError as e:
        print(f"caught: {e}")


def run_gen_happy():
    print("\n=== generator 版 · 正常路径 ===")
    with db_connection("users") as conn:
        conn.execute("SELECT ...")


def run_gen_error():
    print("\n=== generator 版 · 异常路径 ===")
    try:
        with db_connection("users") as conn:
            conn.execute("INSERT ...")
            raise RuntimeError("boom")
    except RuntimeError as e:
        print(f"caught: {e}")


if __name__ == "__main__":
    run_class_happy()
    run_class_error()
    run_gen_happy()
    run_gen_error()
