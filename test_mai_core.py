import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parent
SCRIPT=ROOT/'mai_core.py'

class MAOUCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=pathlib.Path(self.tmp.name)/'test.db'
        self.call('init')

    def tearDown(self):
        self.tmp.cleanup()

    def call(self,*args,ok=True):
        p=subprocess.run([sys.executable,str(SCRIPT),'--db',str(self.db),*map(str,args)],
                         capture_output=True,text=True)
        self.assertEqual(p.returncode==0,ok, p.stdout+'\n'+p.stderr)
        return p.stdout+p.stderr

    def make(self,aid='C1',arm='C'):
        self.call('new','--id',aid,'--arm',arm,'--client','模拟客户甲','--objective','需求诊断',
                  '--deliverable','测试报告','--due','2026-11-01','--price','500','--data-scope','模拟公开数据')

    def test_approval_required(self):
        self.make()
        self.call('event','--id','C1','--kind','work_started','--actor','ai','--dimension','C',
                  '--detail','开始执行',ok=False)
        self.call('approve','--id','C1','--basis','创始人批准')
        self.call('event','--id','C1','--kind','work_started','--actor','ai','--dimension','C','--detail','开始执行')

    def test_human_decision_and_summary(self):
        self.make();self.call('approve','--id','C1','--basis','内部演示')
        self.call('propose','--id','C1','--before','人工整理','--after','删除重复步骤',
                  '--why','重复校对过多','--cost','0')
        self.call('decide','--proposal','1','--action','rejected','--reason','风险仍未知')
        self.call('outcome','--id','C1','--cash-in','500','--cash-out','80','--minutes','300',
                  '--minutes-mai','20','--quality','accepted')
        s=self.call('report')
        self.assertIn('"net_cash": 420.0',s)
        self.assertIn('"net_per_hour": 84.0',s)
        self.assertIn('"pending_proposals": 0',s)

    def test_baseline_cannot_use_maou_proposal(self):
        self.make('B1','B'); self.call('approve','--id','B1','--basis','内部演示')
        self.call('propose','--id','B1','--before','旧','--after','新','--why','test',ok=False)

    def test_no_negative_and_no_overhead_above_total(self):
        self.make();self.call('approve','--id','C1','--basis','test')
        self.call('outcome','--id','C1','--cash-in','100','--cash-out','10','--minutes','10',
                  '--minutes-mai','11','--quality','accepted',ok=False)
        self.call('outcome','--id','C1','--cash-in','-1','--cash-out','10','--minutes','20',
                  '--quality','accepted',ok=False)

if __name__=='__main__': unittest.main()
