#!/usr/bin/env python3
"""MAOU local research prototype — not an authentication, contract or legal-compliance system.

Python 3.9+ stdlib only. SQLite event ledger for one founder's small OPC experiment.
All prices expressed in yuan and time in minutes. No real customer personal data required.
"""
import argparse
import datetime as dt
import json
import sqlite3
from pathlib import Path

NOW = lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS activities (
  id TEXT PRIMARY KEY, arm TEXT NOT NULL CHECK(arm IN ('B','C')),
  client_alias TEXT NOT NULL, objective TEXT NOT NULL, deliverable TEXT NOT NULL,
  due_date TEXT NOT NULL, price_quote REAL NOT NULL CHECK(price_quote>=0),
  data_scope TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  activity_id TEXT NOT NULL REFERENCES activities(id),
  time TEXT NOT NULL, kind TEXT NOT NULL, actor TEXT NOT NULL,
  dimension TEXT NOT NULL CHECK(dimension IN ('G','A','C','F')),
  detail TEXT NOT NULL, evidence_ref TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  activity_id TEXT NOT NULL REFERENCES activities(id),
  created_at TEXT NOT NULL, before_structure TEXT NOT NULL,
  after_structure TEXT NOT NULL, rationale TEXT NOT NULL,
  projected_cost REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending', reviewer TEXT NOT NULL DEFAULT '',
  decided_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS outcomes (
  activity_id TEXT PRIMARY KEY REFERENCES activities(id),
  cash_in REAL NOT NULL DEFAULT 0 CHECK(cash_in>=0),
  cash_out REAL NOT NULL DEFAULT 0 CHECK(cash_out>=0),
  minutes_total INTEGER NOT NULL DEFAULT 0 CHECK(minutes_total>=0),
  minutes_mai INTEGER NOT NULL DEFAULT 0 CHECK(minutes_mai>=0),
  quality TEXT NOT NULL, feedback TEXT NOT NULL, recorded_at TEXT NOT NULL
);
"""


def conn(path):
    db = sqlite3.connect(str(path))
    db.execute('PRAGMA foreign_keys=ON')
    db.row_factory = sqlite3.Row
    return db


def log(db, aid, kind, actor, dimension, detail, evidence=''):
    db.execute('INSERT INTO events(activity_id,time,kind,actor,dimension,detail,evidence_ref) VALUES(?,?,?,?,?,?,?)',
               (aid, NOW(), kind, actor, dimension, detail, evidence))


def activity(db, aid):
    item = db.execute('SELECT * FROM activities WHERE id=?',(aid,)).fetchone()
    if not item:
        raise ValueError(f'未找到活动 {aid}')
    return item


def cmd_init(db, args):
    db.executescript(SCHEMA)
    db.commit()
    print('数据库已创建（或保留原有数据）')


def cmd_new(db, args):
    if not args.data_scope.strip():
        raise ValueError('必须明确数据使用范围')
    db.execute('''INSERT INTO activities(id,arm,client_alias,objective,deliverable,due_date,
                  price_quote,data_scope,created_at) VALUES(?,?,?,?,?,?,?,?,?)''',
               (args.id,args.arm,args.client,args.objective,args.deliverable,args.due,
                args.price,args.data_scope,NOW()))
    log(db,args.id,'activity_created','founder','G','目标与交付承诺已建档；尚未批准')
    db.commit()
    print('活动创建成功；状态 draft，执行或交付前需要人工审批')


def cmd_approve(db, args):
    row=activity(db,args.id)
    if row['status'] != 'draft':
        raise ValueError('仅draft活动可批准')
    if args.reviewer != 'founder':
        raise ValueError('本最小原型仅允许以 founder 标记批准；真实身份验证需外部实现')
    db.execute('UPDATE activities SET status=? WHERE id=?',('approved',args.id))
    log(db,args.id,'activity_approved',args.reviewer,'A',args.basis,args.evidence)
    db.commit()
    print('审批记录成功（程序标记；非可靠电子签名）')


def cmd_event(db,args):
    row=activity(db,args.id)
    if row['status']=='draft' and args.kind not in ('scope_discussion','note'):
        raise ValueError('draft阶段只能写说明事件；执行动作须先批准')
    if row['status'] in ('cancelled','accepted'):
        raise ValueError('结束的活动禁止继续添加执行事件')
    log(db,args.id,args.kind,args.actor,args.dimension,args.detail,args.evidence)
    if row['status']=='approved' and args.kind=='work_started':
        db.execute('UPDATE activities SET status=? WHERE id=?',('active',args.id))
    db.commit()
    print('事件已追加')


def cmd_propose(db,args):
    row=activity(db,args.id)
    if row['arm'] != 'C':
        raise ValueError('B组无需MAOU重构提案；请按成熟工作流记录普通事件')
    if row['status'] in ('cancelled','accepted'):
        raise ValueError('结束的活动不可继续提出方案')
    cur=db.execute('''INSERT INTO proposals(activity_id,created_at,before_structure,after_structure,
                     rationale,projected_cost) VALUES(?,?,?,?,?,?)''',
                  (args.id,NOW(),args.before,args.after,args.why,args.cost))
    log(db,args.id,'restructure_proposed','MAOU-assisted','C',
        f'proposal#{cur.lastrowid}: {args.before} -> {args.after}; 假设成本 {args.cost}')
    db.commit()
    print(f'备选组织方案 #{cur.lastrowid} 已生成；尚不能自动执行')


def cmd_decide(db,args):
    row=db.execute('SELECT * FROM proposals WHERE id=?',(args.proposal,)).fetchone()
    if not row:
        raise ValueError('提案不存在')
    if row['status']!='pending':
        raise ValueError('提案已经有决定，禁止覆盖')
    if args.reviewer!='founder':
        raise ValueError('仅创始人有权批准/拒绝（身份验证需外部完成）')
    db.execute('UPDATE proposals SET status=?,reviewer=?,decided_at=? WHERE id=?',
               (args.action,args.reviewer,NOW(),args.proposal))
    log(db,row['activity_id'],'restructure_decided',args.reviewer,'A',
        f'proposal#{args.proposal}: {args.action}；决策理由：{args.reason}',args.evidence)
    db.commit()
    print(f'提案#{args.proposal}: {args.action}；本程序仅记录，不会自动向第三方发送数据或更改合同')


def cmd_outcome(db,args):
    row=activity(db,args.id)
    if row['status']=='draft':
        raise ValueError('不能对未批准活动录入真实交付结果')
    if row['status']=='cancelled':
        raise ValueError('已取消活动不能交付')
    if args.minutes_mai > args.minutes:
        raise ValueError('MAOU额外记录时间不能超过总时间')
    db.execute('''INSERT INTO outcomes(activity_id,cash_in,cash_out,minutes_total,minutes_mai,
                quality,feedback,recorded_at) VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(activity_id) DO UPDATE SET cash_in=excluded.cash_in,cash_out=excluded.cash_out,
                 minutes_total=excluded.minutes_total,minutes_mai=excluded.minutes_mai,
                 quality=excluded.quality,feedback=excluded.feedback,recorded_at=excluded.recorded_at''',
               (args.id,args.cash_in,args.cash_out,args.minutes,args.minutes_mai,
                args.quality,args.feedback,NOW()))
    status='accepted' if args.quality=='accepted' else 'delivered'
    db.execute('UPDATE activities SET status=? WHERE id=?',(status,args.id))
    log(db,args.id,'outcome_recorded','founder','F',
        f'实收={args.cash_in} 成本={args.cash_out} 总分钟={args.minutes} MAOU开销分钟={args.minutes_mai} 质量={args.quality}')
    db.commit()
    print('结果已记录；注意实收≠报价，总时间必须包括建模、审批、售后')


def summary(db):
    rows=db.execute('''SELECT a.arm, COUNT(*) n, COUNT(o.activity_id) outcomes,
                COALESCE(SUM(o.cash_in),0) cash_in, COALESCE(SUM(o.cash_out),0) cash_out,
                COALESCE(SUM(o.minutes_total),0) mins, COALESCE(SUM(o.minutes_mai),0) mai_mins,
                SUM(CASE WHEN o.quality='accepted' THEN 1 ELSE 0 END) accepted
                FROM activities a LEFT JOIN outcomes o ON o.activity_id=a.id
                GROUP BY a.arm ORDER BY a.arm''').fetchall()
    return [{**dict(r), 'net_cash':round(r['cash_in']-r['cash_out'],2),
             'net_per_hour': round((r['cash_in']-r['cash_out'])*60/r['mins'],2) if r['mins'] else None}
            for r in rows]


def cmd_report(db,args):
    out={'arms':summary(db),
         'pending_proposals':db.execute("SELECT count(*) FROM proposals WHERE status='pending'").fetchone()[0],
         'note':'描述性过程数据。小样本与任务异质性下不能当作因果检验。'}
    print(json.dumps(out,ensure_ascii=False,indent=2))


def cmd_show(db,args):
    row=activity(db,args.id)
    events=[dict(x) for x in db.execute('SELECT * FROM events WHERE activity_id=? ORDER BY id',(args.id,))]
    prop=[dict(x) for x in db.execute('SELECT * FROM proposals WHERE activity_id=? ORDER BY id',(args.id,))]
    outcome=db.execute('SELECT * FROM outcomes WHERE activity_id=?',(args.id,)).fetchone()
    print(json.dumps({'activity':dict(row),'events':events,'proposals':prop,'outcome':dict(outcome) if outcome else None},ensure_ascii=False,indent=2))


def make_parser():
    p=argparse.ArgumentParser(description='MAOU一人公司组织实验账本（离线，无AI API自动调用）')
    p.add_argument('--db',default='maou.sqlite3',help='SQLite数据库路径')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    n=sub.add_parser('new');n.add_argument('--id',required=True);n.add_argument('--arm',choices=['B','C'],required=True)
    n.add_argument('--client',required=True);n.add_argument('--objective',required=True)
    n.add_argument('--deliverable',required=True);n.add_argument('--due',required=True)
    n.add_argument('--price',type=float,default=0);n.add_argument('--data-scope',required=True)
    a=sub.add_parser('approve');a.add_argument('--id',required=True);a.add_argument('--reviewer',default='founder')
    a.add_argument('--basis',required=True);a.add_argument('--evidence',default='')
    e=sub.add_parser('event');e.add_argument('--id',required=True);e.add_argument('--kind',required=True)
    e.add_argument('--actor',required=True);e.add_argument('--dimension',choices=['G','A','C','F'],required=True)
    e.add_argument('--detail',required=True);e.add_argument('--evidence',default='')
    t=sub.add_parser('propose');t.add_argument('--id',required=True);t.add_argument('--before',required=True)
    t.add_argument('--after',required=True);t.add_argument('--why',required=True);t.add_argument('--cost',type=float,default=0)
    d=sub.add_parser('decide');d.add_argument('--proposal',type=int,required=True)
    d.add_argument('--action',choices=['approved','rejected'],required=True);d.add_argument('--reason',required=True)
    d.add_argument('--reviewer',default='founder');d.add_argument('--evidence',default='')
    o=sub.add_parser('outcome');o.add_argument('--id',required=True);o.add_argument('--cash-in',type=float,required=True)
    o.add_argument('--cash-out',type=float,required=True);o.add_argument('--minutes',type=int,required=True)
    o.add_argument('--minutes-mai',type=int,default=0);o.add_argument('--quality',choices=['accepted','needs_revision','failed'],required=True)
    o.add_argument('--feedback',default='')
    sub.add_parser('report')
    s=sub.add_parser('show');s.add_argument('--id',required=True)
    return p


def main(argv=None):
    p=make_parser();args=p.parse_args(argv)
    path=Path(args.db);path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with conn(path) as db:
            cmd={'init':cmd_init,'new':cmd_new,'approve':cmd_approve,'event':cmd_event,
                 'propose':cmd_propose,'decide':cmd_decide,'outcome':cmd_outcome,
                 'report':cmd_report,'show':cmd_show}[args.command]
            cmd(db,args)
    except (sqlite3.Error,ValueError) as exc:
        p.exit(2,f'错误: {exc}\n')

if __name__=='__main__':
    main()
