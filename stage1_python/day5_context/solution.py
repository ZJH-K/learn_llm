# Day 5 - 数据库连接 with 管理器
#
# 任务:实现两版"模拟数据库事务"的上下文管理器,行为等价
#   1) DBConnection        —— class 形式,__enter__ / __exit__
#   2) db_connection(name) —— @contextmanager + generator 形式
#
# 共用部分:一个伪 DB 对象,提供 .execute(sql),内部 pending 列表累积未提交语句
#
# 出块行为(两版必须一致):
#   无异常 → commit (N statements) → close
#   有异常 → rollback (N statements discarded) → close → 异常继续向上抛
#
# 写完跑:uv run python main.py
# 期望输出在 main.py 里有注释说明
from contextlib import contextmanager

# TODO: 写一个 _FakeDB 类,被两版共用
class _FakeDB:
    def __init__(self, name):
        # TODO 1:存 name(留给 connect 时打印用)
        self.name = name
        # TODO 2:初始化一个空 list,叫 pending,用来累积未提交的 SQL
        self.pending = []

    def execute(self, sql):
        # TODO 3:打印 "[DB] exec: <sql>"
        print(f"[DB] exec: {sql}")
        # TODO 4:把 sql 追加到 pending 列表
        self.pending.append(sql)

def _log_commit(n):
      print(f"[DB] commit ({n} statements)")

def _log_rollback(n):
    print(f"[DB] rollback ({n} statements discarded)")

# TODO: 版本 A —— class 形式
class DBConnection: 
    def __init__(self, name):
        self.name = name
    
    def __enter__(self):
        print(f"[DB] connect to {self.name}")
        self.db = _FakeDB(self.name)
        return self.db
    
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            _log_commit(len(self.db.pending))
        else:
           _log_rollback(len(self.db.pending))
        print("[DB] close")
          
# TODO: 版本 B —— @contextmanager 形式
@contextmanager
def db_connection(name):
    print(f"[DB] connect to {name}")
    db = _FakeDB(name)
    try:
        yield db
    except Exception:
        _log_rollback(len(db.pending))
        raise
    else:
        _log_commit(len(db.pending))
    finally:
        print("[DB] close")
