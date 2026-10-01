import json
import unittest
from unittest.mock import patch

from scripts import fetch_signals


class _Response:
    def __init__(self, body):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.body


class TestFetchSignals(unittest.TestCase):
    def setUp(self):
        self.original = {
            key: getattr(fetch_signals, key)
            for key in (
                "CAR_NEWREG_API_URL", "CAR_NEWREG_KEY", "CAR_NEWREG_FORM_ID",
                "CAR_NEWREG_STYLE_NUM", "CAR_NEWREG_EXTRA_PARAMS", "CAR_NEWREG_START_DT",
                "CAR_NEWREG_END_DT", "CAR_NEWREG_PAGE_NO", "CAR_NEWREG_NUM_OF_ROWS",
            )
        }

    def tearDown(self):
        for key, value in self.original.items():
            setattr(fetch_signals, key, value)

    def test_data_go_url_works_without_stat_molit_form_style(self):
        fetch_signals.CAR_NEWREG_API_URL = "https://apis.data.go.kr/tsm/vehicle/new"
        fetch_signals.CAR_NEWREG_KEY = "encoded-key"
        fetch_signals.CAR_NEWREG_FORM_ID = ""
        fetch_signals.CAR_NEWREG_STYLE_NUM = ""
        fetch_signals.CAR_NEWREG_EXTRA_PARAMS = json.dumps({"sido": "서울", "vehicleType": "승용"}, ensure_ascii=False)
        fetch_signals.CAR_NEWREG_START_DT = "202607"
        fetch_signals.CAR_NEWREG_END_DT = "202607"
        captured = {}
        body = json.dumps({"response": {"header": {"resultCode": "00"}, "body": {"totalCount": 12345}}})

        def fake_open(url, timeout=20):
            captured["url"] = url
            return _Response(body)

        with patch.object(fetch_signals.urllib.request, "urlopen", side_effect=fake_open):
            result = fetch_signals.fetch_car_newreg()

        self.assertEqual(result["count"], 12345)
        self.assertEqual(result["source"], "data.go.kr")
        self.assertIn("serviceKey=encoded-key", captured["url"])
        self.assertIn("dataType=JSON", captured["url"])
        self.assertIn("sido=%EC%84%9C%EC%9A%B8", captured["url"])
        self.assertNotIn("form_id", captured["url"])
        self.assertNotIn("style_num", captured["url"])

    def test_monthly_series_uses_latest_count_and_computes_mom(self):
        fetch_signals.CAR_NEWREG_API_URL = "https://apis.data.go.kr/tsm/vehicle/new"
        fetch_signals.CAR_NEWREG_KEY = "encoded-key"
        fetch_signals.CAR_NEWREG_FORM_ID = ""
        fetch_signals.CAR_NEWREG_STYLE_NUM = ""
        fetch_signals.CAR_NEWREG_EXTRA_PARAMS = ""
        body = json.dumps({"response": {"body": {"items": {"item": [
            {"registYm": "202606", "newRegCnt": "1000"},
            {"registYm": "202607", "newRegCnt": "1250"},
        ]}}}})
        with patch.object(fetch_signals.urllib.request, "urlopen", return_value=_Response(body)):
            result = fetch_signals.fetch_car_newreg()
        self.assertEqual(result["count"], 1250)
        self.assertEqual(result["period"], "202607")
        self.assertEqual(result["mom"], 25.0)

    def test_stat_molit_registration_form_is_stock_not_new(self):
        # 2026-10 실측: form 5498은 '자동차등록대수현황 시도별'(누적) — formList 행=시도×월, 열='차종>용도'
        fetch_signals.CAR_NEWREG_API_URL = "http://stat.molit.go.kr/portal/openapi/service/rest/getList.do"
        fetch_signals.CAR_NEWREG_KEY = "key"
        fetch_signals.CAR_NEWREG_FORM_ID = "5498"
        fetch_signals.CAR_NEWREG_STYLE_NUM = "2"
        fetch_signals.CAR_NEWREG_EXTRA_PARAMS = ""
        fetch_signals.CAR_NEWREG_START_DT = "202606"
        fetch_signals.CAR_NEWREG_END_DT = "202607"
        body = json.dumps({"result_status": {"status_code": "INFO-000"}, "result_data": {"formName": "자동차등록대수현황 시도별", "formList": [
            {"date": "202606", "시도명": "서울", "승용>계": 1000, "승용>자가용": 900, "화물>계": 100},
            {"date": "202606", "시도명": "부산", "승용>계": 500, "화물>계": 50},
            {"date": "202607", "시도명": "서울", "승용>계": 1010, "승용>자가용": 905, "화물>계": 101},
            {"date": "202607", "시도명": "부산", "승용>계": 503, "화물>계": 50},
        ]}}, ensure_ascii=False)
        with patch.object(fetch_signals.urllib.request, "urlopen", return_value=_Response(body)):
            result = fetch_signals.fetch_car_newreg()
        self.assertEqual(result["kind"], "stock")
        self.assertEqual(result["count"], 1664)   # '>계' 열만, 시도 합산(용도별 중복 제외)
        self.assertEqual(result["net_change"], 14)
        self.assertEqual(result["period"], "202607")
        note = fetch_signals.build_triggers({}, {}, None, result)["driver"]["note"]
        self.assertIn("등록대수(누적", note)
        self.assertNotIn("신규등록", note)

    def test_stat_molit_url_still_requires_form_style(self):
        fetch_signals.CAR_NEWREG_API_URL = "http://stat.molit.go.kr/portal/openapi/service/rest/getList.do"
        fetch_signals.CAR_NEWREG_KEY = "key"
        fetch_signals.CAR_NEWREG_FORM_ID = ""
        fetch_signals.CAR_NEWREG_STYLE_NUM = ""
        result = fetch_signals.fetch_car_newreg()
        self.assertIsNone(result["count"])
        self.assertIn("FORM_ID", result["error"])


if __name__ == "__main__":
    unittest.main()
