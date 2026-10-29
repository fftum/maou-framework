# 离线账本示例

需要 Python 3.9+。无网络调用，无第三方依赖。

```bash
python3 demo_offline.py
python3 -m unittest discover -s . -p 'test_*.py' -v
```

`demo_offline.py` 在临时目录建立一个虚构活动，登记批准、执行事件、重构提案、拒绝决定与结果，打印报表后清理数据库。

如需手工试用，可在本地新建测试库：

```bash
python3 mai_core.py --db demo.sqlite3 init
python3 mai_core.py --db demo.sqlite3 new --id C001 --arm C --client '虚构对象' --objective '检查示例' --deliverable '一份模拟报告' --due '2026-11-01' --data-scope '仅虚构数据'
python3 mai_core.py --db demo.sqlite3 approve --id C001 --basis '维护者批准内部模拟'
python3 mai_core.py --db demo.sqlite3 event --id C001 --kind work_started --actor assistant --dimension C --detail '开始模拟工作'
python3 mai_core.py --db demo.sqlite3 show --id C001
```

`approve` 只写一条批准标记。任何能运行程序或修改 SQLite 的人都可能改变数据；程序没有可靠身份校验。

B 组是成熟普通工作流的记账组；C 组多了专用重构提案入口。程序不会替你执行 B/C 组任务，分组和实验设计仍须人工安排。

结果报表中的 `cash_in` 是录入的实收，`cash_out` 是录入的增量现金成本，`minutes_mai` 是总时间中用于框架建档与管理的部分。SQLite 不核验输入真假；报表只汇总录入数据。
