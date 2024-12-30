import shodan
import requests

# 替換為您的 Shodan 和 FOFA API 密鑰
SHODAN_API_KEY = 'YOUR_SHODAN_API_KEY'
FOFA_EMAIL = 'YOUR_FOFA_EMAIL'
FOFA_API_KEY = 'YOUR_FOFA_API_KEY'

# 初始化 Shodan 客戶端
shodan_api = shodan.Shodan(SHODAN_API_KEY)

# 載入目標 IP 清單的文件名稱
target_file = 'targets.txt'
# 保存有開啟 3389 的 IP 的文件
output_file = 'final_rdp.txt'

# FOFA API 的基礎 URL
FOFA_API_URL = 'https://fofa.info/api/v1/search/all'

def fetch_fofa_results():
    """使用 FOFA API 搜索開放 3389 的 IP"""
    query = 'port=3389'
    params = {
        'email': FOFA_EMAIL,
        'key': FOFA_API_KEY,
        'qbase64': query.encode('utf-8').decode('utf-8'),
        'fields': 'ip'
    }
    try:
        response = requests.get(FOFA_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return set(result['ip'] for result in data['results'])
    except Exception as e:
        print(f"Error fetching FOFA results: {e}")
        return set()

def fetch_shodan_results(target_ips):
    """使用 Shodan API 檢查開放 3389 的 IP"""
    open_rdp_ips = set()
    for ip in target_ips:
        try:
            print(f"Checking IP: {ip} via Shodan")
            host = shodan_api.host(ip)
            if any(service['port'] == 3389 for service in host.get('data', [])):
                print(f"[+] {ip} has port 3389 open (Shodan)")
                open_rdp_ips.add(ip)
        except shodan.APIError as e:
            print(f"Error checking IP {ip} via Shodan: {e}")
    return open_rdp_ips

try:
    # 從文件讀取目標 IP
    with open(target_file, 'r') as f:
        target_ips = set(line.strip() for line in f if line.strip())

    print(f"Loaded {len(target_ips)} target IPs from {target_file}")

    # 從 FOFA 獲取開放 3389 的 IP
    print("Fetching FOFA results...")
    fofa_ips = fetch_fofa_results()
    print(f"FOFA found {len(fofa_ips)} IPs with port 3389 open")

    # 與目標 IP 進行交集
    fofa_target_ips = target_ips.intersection(fofa_ips)
    print(f"{len(fofa_target_ips)} IPs matched from FOFA results")

    # 從 Shodan 檢查交集結果
    print("Checking FOFA results with Shodan...")
    final_rdp_ips = fetch_shodan_results(fofa_target_ips)

    # 保存最終結果
    with open(output_file, 'w') as f:
        f.write("\n".join(final_rdp_ips))
    print(f"Saved {len(final_rdp_ips)} IPs with port 3389 open to {output_file}")

except FileNotFoundError:
    print(f"Error: File {target_file} not found.")
except Exception as e:
    print(f"An error occurred: {e}")
