import json, urllib.request, urllib.error, datetime

from config import PROXY as PROXY_URL, PROXY_HOST, PROXY_PORT


def _proxy_alive():
    import socket
    s = socket.socket()
    s.settimeout(1.5)
    try:
        s.connect((PROXY_HOST, PROXY_PORT))
        return True
    except Exception:
        return False
    finally:
        s.close()


if _proxy_alive():
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'http': PROXY_URL, 'https': PROXY_URL}))
else:
    print('[warn] 代理 %s:%d 未监听，改用直连' % (PROXY_HOST, PROXY_PORT))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
opener.addheaders = [('User-Agent', 'Mozilla/5.0')]


def get(url, timeout=60):
    return opener.open(url, timeout=timeout).read()


print('=== 1. CISA KEV (recently added) ===')
try:
    data = json.loads(get('https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'))
    vs = sorted(data['vulnerabilities'], key=lambda x: x['dateAdded'], reverse=True)
    print('catalogVersion:', data.get('catalogVersion'), '| total:', data.get('count'))
    for v in vs[:14]:
        print(v['dateAdded'], '|', v['cveID'], '|', v['vendorProject'], v['product'], '|',
              v['vulnerabilityName'][:75], '| ransom:', v.get('knownRansomwareCampaignUse'))
except Exception as e:
    print('ERR', type(e).__name__, e)

print()
print('=== 2. GitHub Security Advisory (recent) ===')
try:
    advs = json.loads(get('https://api.github.com/advisories?per_page=20&sort=published&direction=desc'))
    for a in advs[:14]:
        cve = a.get('cve_id') or '-'
        sev = (a.get('severity') or '-')
        pkg = ''
        if a.get('vulnerabilities'):
            v0 = a['vulnerabilities'][0].get('package') or {}
            pkg = v0.get('name') or ''
        print(a.get('published_at', '')[:10], '|', sev, '|', cve, '|', pkg, '|', a.get('summary', '')[:80])
except Exception as e:
    print('ERR', type(e).__name__, e)

print()
print('=== 3. Hacker News front page (last 24h, >80 pts) ===')
try:
    since = int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)).timestamp())
    hn = json.loads(get(f'https://hn.algolia.com/api/v1/search?tags=story&numericFilters=points>80,created_at_i>{since}&hitsPerPage=25'))
    for h in hn['hits'][:20]:
        print(h['points'], 'pts |', h.get('title', '')[:95], '|', (h.get('url') or '')[:70])
except Exception as e:
    print('ERR', type(e).__name__, e)
