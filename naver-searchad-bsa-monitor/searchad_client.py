#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 검색광고(Search AD) Open API 최소 클라이언트.

인증 방식 (공식 문서: https://naver.github.io/searchad-apidoc/):
  - 매 요청마다 HMAC-SHA256 서명을 만들어 헤더에 실어 보낸다.
  - 서명 대상 문자열은 "{timestamp}.{method}.{uri}" (uri는 쿼리스트링 제외, path만).
  - 헤더: X-Timestamp, X-API-KEY, X-Customer, X-Signature

환경변수 (필수):
  NAVER_SEARCHAD_API_KEY
  NAVER_SEARCHAD_SECRET_KEY
  NAVER_SEARCHAD_CUSTOMER_ID

외부 라이브러리 의존 없음(stdlib만 사용) — 이 저장소의 news_watch.py와 동일한 방침.
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.searchad.naver.com"


class SearchAdAuthError(RuntimeError):
    """환경변수 미설정 등 인증 정보 자체가 없을 때."""


class SearchAdAPIError(RuntimeError):
    """API가 4xx/5xx로 응답했을 때 (권한 없음, 서명 오류, 잘못된 파라미터 등)."""

    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body}")


def _make_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"
    raw = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(raw).decode("utf-8")


class SearchAdClient:
    def __init__(self, api_key=None, secret_key=None, customer_id=None):
        self.api_key = api_key or os.environ.get("NAVER_SEARCHAD_API_KEY")
        self.secret_key = secret_key or os.environ.get("NAVER_SEARCHAD_SECRET_KEY")
        self.customer_id = customer_id or os.environ.get("NAVER_SEARCHAD_CUSTOMER_ID")
        if not (self.api_key and self.secret_key and self.customer_id):
            raise SearchAdAuthError(
                "NAVER_SEARCHAD_API_KEY / NAVER_SEARCHAD_SECRET_KEY / "
                "NAVER_SEARCHAD_CUSTOMER_ID 환경변수를 모두 설정하세요."
            )

    def _headers(self, method, uri):
        timestamp = str(int(time.time() * 1000))
        signature = _make_signature(timestamp, method, uri, self.secret_key)
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": self.api_key,
            "X-Customer": str(self.customer_id),
            "X-Signature": signature,
        }

    def get(self, uri, params=None):
        """uri: 쿼리스트링 없는 path만 (예: '/ncc/campaigns'). params는 별도 dict로."""
        method = "GET"
        headers = self._headers(method, uri)
        url = BASE_URL + uri
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise SearchAdAPIError(e.code, body) from None

    def list_campaigns(self):
        """전체 캠페인 목록. 필드 예: nccCampaignId, name, campaignTp, status, userLock, regTm ..."""
        return self.get("/ncc/campaigns")

    def list_adgroups(self, ncc_campaign_id):
        """캠페인 하위 광고그룹 목록. 필드 예: nccAdgroupId, name, status, userLock, regTm ..."""
        return self.get("/ncc/adgroups", params={"nccCampaignId": ncc_campaign_id})


def _smoke_test():
    """자격증명 확인 + 원본 응답 필드 확인용. 실제 계정 필드명이 문서와 다를 수 있어
    도구를 처음 쓸 때 반드시 이 커맨드로 실제 캠페인/광고그룹 JSON을 눈으로 확인할 것."""
    client = SearchAdClient()
    campaigns = client.list_campaigns()
    print(json.dumps(campaigns, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        _smoke_test()
    except SearchAdAuthError as e:
        sys.exit(str(e))
    except SearchAdAPIError as e:
        sys.exit(f"API 오류: {e}")
