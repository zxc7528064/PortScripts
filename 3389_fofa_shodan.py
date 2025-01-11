import shodan
import requests
import base64

# 替換為您的 Shodan 和 FOFA API 密鑰
SHODAN_API_KEY = ''
FOFA_EMAIL = ''
FOFA_API_KEY = ''

# 初始化 Shodan 客戶端
shodan_api = shodan.Shodan(SHODAN_API_KEY)

# 載入目標 IP 清單的文件名稱
target_file = 'target.txt'
# 保存有開啟 3389 的 IP 的文件
output_file = 'final_rdp.txt'

# FOFA API 的基礎 URL
FOFA_API_URL = 'https://fofa.info/api/v1/search/all'

def fetch_fofa_results(ip):
    """使用 FOFA API 搜索指定 IP 的 3389 端口"""
    query = f'ip="{ip}" && port=3389'
    query_base64 = base64.b64encode(query.encode('utf-8')).decode('utf-8')
    params = {
        'email': FOFA_EMAIL,
        'key': FOFA_API_KEY,
        'qbase64': query_base64,
        'fields': 'ip'
    }
    try:
        response = requests.get(FOFA_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if 'results' in data and data['results']:
            print(f"[FOFA] {ip} has port 3389 open")
            return True
        else:
            print(f"[FOFA] {ip} does not have port 3389 open")
            return False
    except Exception as e:
        print(f"Error fetching FOFA results for {ip}: {e}")
        return False

def fetch_shodan_results(ip):
    """使用 Shodan API 檢查指定 IP 的 3389 端口"""
    try:
        print(f"Checking IP: {ip} via Shodan")
        host = shodan_api.host(ip)
        if any(service['port'] == 3389 for service in host.get('data', [])):
            print(f"[Shodan] {ip} has port 3389 open")
            return True
        else:
            print(f"[Shodan] {ip} does not have port 3389 open")
            return False
    except shodan.APIError as e:
        print(f"Error checking IP {ip} via Shodan: {e}")
        return False

try:
    # 從文件讀取目標 IP
    with open(target_file, 'r', encoding='utf-8') as f:
        target_ips = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(target_ips)} target IPs from {target_file}")

    final_rdp_ips = []

    for ip in target_ips:
        print(f"\nChecking IP: {ip}")
        fofa_open = fetch_fofa_results(ip)
        shodan_open = fetch_shodan_results(ip)

        if fofa_open and shodan_open:
            final_rdp_ips.append(ip)

    # 保存最終結果
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(final_rdp_ips))
    print(f"\nSaved {len(final_rdp_ips)} IPs with port 3389 open to {output_file}")

except FileNotFoundError:
    print(f"Error: File {target_file} not found.")
except Exception as e:
    print(f"An error occurred: {e}")
