#!/usr/bin/env python3
"""Google Search Console OAuth refresh token으로 최근 검색 쿼리를 비공개 수집한다."""
import json, os, urllib.parse, urllib.request
from datetime import date, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data/search-console.json'

def post(url, data, headers=None):
    req=urllib.request.Request(url,data=data,headers=headers or {},method='POST')
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def fetch(site, client_id, client_secret, refresh_token, days=28):
    token=post('https://oauth2.googleapis.com/token',urllib.parse.urlencode({'client_id':client_id,'client_secret':client_secret,'refresh_token':refresh_token,'grant_type':'refresh_token'}).encode())['access_token']
    end=date.today()-timedelta(days=2); start=end-timedelta(days=days-1)
    body=json.dumps({'startDate':start.isoformat(),'endDate':end.isoformat(),'dimensions':['query','page'],'rowLimit':25000}).encode()
    url='https://searchconsole.googleapis.com/webmasters/v3/sites/'+urllib.parse.quote(site,safe='')+'/searchAnalytics/query'
    raw=post(url,body,{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    rows=[]
    for x in raw.get('rows',[]):
        keys=x.get('keys',[]); rows.append({'query':keys[0] if keys else '', 'page':keys[1] if len(keys)>1 else '', 'clicks':x.get('clicks',0),'impressions':x.get('impressions',0),'ctr':x.get('ctr',0),'position':x.get('position',0)})
    return {'asof':end.isoformat(),'site':site,'rows':rows}

def main():
    names=('GSC_SITE_URL','GSC_CLIENT_ID','GSC_CLIENT_SECRET','GSC_REFRESH_TOKEN')
    values=[os.getenv(x,'') for x in names]
    if not all(values): print('⚠ Search Console Secret 미설정 — 기존 입력 유지'); return None
    data=fetch(*values); OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"✔ Search Console · {len(data['rows'])}개 쿼리 행 · {data['asof']}"); return data
if __name__=='__main__':main()
