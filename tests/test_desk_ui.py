import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import desk_ui


class DeskUiTest(unittest.TestCase):
    def test_spinoff_start_date_validation(self):
        self.assertEqual(desk_ui.validate_spinoff({'start_date':'2025-01-02'}),'2025-01-02')
        for item in ('not a date','2025-02-30','9999-01-01','2025-01-02;bad'):
            with self.assertRaises(ValueError): desk_ui.validate_spinoff({'start_date':item})

    def test_spinoff_page_only_displays_saved_report_inside_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs=Path(tmp).resolve()
            report=runs/'spinoff-screen-2025.md'
            report.write_text('Run date: 2025-01-01 | Price date: unavailable | Index date: unavailable\n\nscreens, not recommendations\n',encoding='utf-8')
            class Process:
                stdout=iter([f'Screen report: {report}\n'])
                def wait(self): return 0
            desk_ui.jobs['spinoff-test']={'status':'running','events':[]}
            with patch.object(desk_ui,'SPINOFF_RUNS',runs), patch.object(desk_ui.subprocess,'Popen',return_value=Process()) as popen:
                desk_ui.execute_spinoff('spinoff-test','2025-01-01')
            result=desk_ui.jobs.pop('spinoff-test')
            self.assertEqual(result['status'],'complete')
            self.assertIn('screens, not recommendations',result['report_html'])
            self.assertIn('2025-01-01',popen.call_args.args[0])

    def test_spinoff_job_accepts_date_and_rejects_cross_origin(self):
        server=desk_ui.ThreadingHTTPServer(('127.0.0.1',0),desk_ui.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        called=threading.Event()
        def fake_execute(job_id,start):
            with desk_ui.lock: desk_ui.jobs[job_id].update(status='complete',events=[start],report_html='done',report_path='saved')
            called.set()
        try:
            with patch.object(desk_ui,'execute_spinoff',fake_execute):
                req=Request(url+'/api/spinoff-jobs',data=json.dumps({'start_date':'2025-01-01'}).encode(),headers={'Content-Type':'application/json','Origin':url})
                job_id=json.loads(urlopen(req,timeout=5).read())['job_id']
                self.assertTrue(called.wait(5))
                result=json.loads(urlopen(url+'/api/jobs/'+job_id,timeout=5).read())
                self.assertEqual(result['events'],['2025-01-01'])
                desk_ui.jobs.pop(job_id)
            req=Request(url+'/api/spinoff-jobs',data=b'{}',headers={'Content-Type':'application/json','Origin':'http://evil.invalid'})
            with self.assertRaises(HTTPError) as err: urlopen(req,timeout=5)
            self.assertEqual(err.exception.code,403)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_validation_and_argument_safety(self):
        self.assertEqual(desk_ui.validate({"ticker":"abc", "peers":"def, ghi", "price":"12.50"}), ("ABC", ["DEF", "GHI"], "12.50"))
        for payload in ({"ticker":"ABC;whoami"}, {"ticker":"ABC", "price":"-1"}, {"ticker":"ABC", "peers":"DEF;X"}):
            with self.assertRaises(ValueError):
                desk_ui.validate(payload)

    def test_execute_displays_only_a_real_verified_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp).resolve()
            report = runs / "run" / "verified_report.md"
            report.parent.mkdir()
            report.write_text("Filings: source\n\n| Number | Mark |\n|---|---|\n| 1 | correct |\n\n<script>alert(1)</script>\n", encoding="utf-8")
            class Process:
                stdout = iter(["Step 1 started\n", "Research Analyst\n", f"Verified report: {report}\n"])
                def wait(self): return 0
            desk_ui.jobs["test"] = {"status":"running", "events":[]}
            with patch.object(desk_ui, "RUNS", runs), patch.object(desk_ui.subprocess, "Popen", return_value=Process()) as popen:
                desk_ui.execute("test", "ABC", ["DEF"], "10")
            job = desk_ui.jobs.pop("test")
            self.assertEqual(job["status"], "complete")
            self.assertEqual(job["events"], ["Step 1 started", "Research Analyst"])
            self.assertIn("<table>", job["report_html"])
            self.assertNotIn("<script>", job["report_html"])
            self.assertEqual(popen.call_args.args[0][-5:], ["ABC", "--peers", "DEF", "--price", "10"])

    def test_failed_run_does_not_display_old_report(self):
        class Process:
            stdout = iter(["Error executing listener: failed\n"])
            def wait(self): return 0
        desk_ui.jobs["test"] = {"status":"running", "events":[]}
        with patch.object(desk_ui.subprocess, "Popen", return_value=Process()):
            desk_ui.execute("test", "ABC", [], None)
        job = desk_ui.jobs.pop("test")
        self.assertEqual(job["status"], "error")
        self.assertNotIn("report_html", job)

    def test_http_page_validation_and_same_origin(self):
        server = desk_ui.ThreadingHTTPServer(("127.0.0.1", 0), desk_ui.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            self.assertIn(b"Equity Research Desk", urlopen(url, timeout=5).read())
            request = Request(url + "/api/jobs", data=json.dumps({"ticker":"ABC;bad"}).encode(), headers={"Content-Type":"application/json", "Origin":url})
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=5)
            self.assertEqual(error.exception.code, 400)
            request = Request(url + "/api/jobs", data=b'{}', headers={"Content-Type":"application/json", "Origin":"http://example.invalid"})
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=5)
            self.assertEqual(error.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_http_valid_run_returns_progress_and_report(self):
        server = desk_ui.ThreadingHTTPServer(("127.0.0.1", 0), desk_ui.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        finished = threading.Event()
        def fake_execute(job_id, ticker, peers, price):
            with desk_ui.lock:
                desk_ui.jobs[job_id].update(status="complete", events=["Step 1 started", "Verifier"], report_html="<p>Filings: test</p>", report_path="saved")
            finished.set()
        try:
            with patch.object(desk_ui, "execute", fake_execute):
                request = Request(url + "/api/jobs", data=json.dumps({"ticker":"ABC"}).encode(), headers={"Content-Type":"application/json", "Origin":url})
                job_id = json.loads(urlopen(request, timeout=5).read())["job_id"]
                self.assertTrue(finished.wait(5))
                result = json.loads(urlopen(url + "/api/jobs/" + job_id, timeout=5).read())
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["events"][-1], "Verifier")
            self.assertIn("Filings", result["report_html"])
            desk_ui.jobs.pop(job_id)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
