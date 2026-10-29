"""Run one synthetic ledger example. No network, model calls or external actions."""
import pathlib
import subprocess
import sys
import tempfile


def main():
    script = pathlib.Path(__file__).with_name('mai_core.py')
    with tempfile.TemporaryDirectory(prefix='maou-demo-') as folder:
        db = pathlib.Path(folder) / 'synthetic.sqlite3'
        steps = [
            ['init'],
            ['new', '--id', 'C001', '--arm', 'C', '--client', '虚构对象',
             '--objective', '检查组织提案记账', '--deliverable', '一份模拟报告',
             '--due', '2026-11-01', '--data-scope', '仅虚构数据'],
            ['approve', '--id', 'C001', '--basis', '维护者批准内部模拟'],
            ['event', '--id', 'C001', '--kind', 'work_started', '--actor', 'assistant',
             '--dimension', 'C', '--detail', '模拟开始；无外部执行'],
            ['propose', '--id', 'C001', '--before', '逐项检查', '--after', '抽检',
             '--why', '比较审核成本'],
            ['decide', '--proposal', '1', '--action', 'rejected',
             '--reason', '尚无证据证明抽检满足质量要求'],
            ['outcome', '--id', 'C001', '--cash-in', '0', '--cash-out', '10',
             '--minutes', '120', '--minutes-mai', '15', '--quality', 'accepted',
             '--feedback', '全部数值虚构；不是客户成果'],
            ['report'],
        ]
        print('虚构演示：提案被拒绝；结果仅用于检查报表。', flush=True)
        for args in steps:
            subprocess.run([sys.executable, str(script), '--db', str(db), *args], check=True)


if __name__ == '__main__':
    main()
