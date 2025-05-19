import shodan
import requests
import base64

# === 你的 API Key（請自行替換） ===
SHODAN_API_KEY = ''
FOFA_EMAIL = ''
FOFA_API_KEY = ''

# === 檔案設定 ===
target_file = 'target.txt'
output_file = 'final_rdp.txt'

# === FOFA 設定 ===
FOFA_API_URL = 'https://fofa.info/api/v1/search/all'

# === 初始化 Shodan ===
shodan_api = shodan.Shodan(SHODAN_API_KEY)

# === FOFA 查詢 ===
def fetch_fofa_results(ip):
    query = f'ip="{ip}" && (port=3389 || port=33890)'
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
            print(f"[🟢 FOFA] {ip} => 開啟 RDP (3389/33890)")
            return True
        else:
            print(f"[⚪ FOFA] {ip} => 未發現開放")
            return False
    except Exception as e:
        print(f"[❌ FOFA] {ip} 發生錯誤: {e}")
        return False

# === SHODAN 查詢 ===
def fetch_shodan_results(ip):
    try:
        host = shodan_api.host(ip)
        open_ports = [service['port'] for service in host.get('data', [])]
        if 3389 in open_ports or 33890 in open_ports:
            print(f"[🟢 SHODAN] {ip} => 開啟 RDP: {open_ports}")
            return True
        else:
            print(f"[⚪ SHODAN] {ip} => 未開放 RDP: {open_ports}")
            return False
    except shodan.APIError as e:
        print(f"[❌ SHODAN] {ip} 發生錯誤: {e}")
        return False

# === 主程序 ===
try:
    with open(target_file, 'r', encoding='utf-8') as f:
        target_ips = [line.strip() for line in f if line.strip()]

    print(f"📂 載入 {len(target_ips)} 筆目標 IP")

    final_rdp_ips = []

    for ip in target_ips:
        print(f"\n🔍 正在檢查 IP: {ip}")
        fofa_open = fetch_fofa_results(ip)
        shodan_open = fetch_shodan_results(ip)

        if fofa_open or shodan_open:
            print(f"[✅ 命中] {ip} 被記錄下來")
            final_rdp_ips.append(ip)
        else:
            print(f"[❌ 跳過] {ip} 未發現 RDP 開放")

    # 寫入結果
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_rdp_ips))

    print(f"\n✅ 共 {len(final_rdp_ips)} 筆 IP 被寫入：{output_file}")

except FileNotFoundError:
    print(f"[❌] 找不到檔案：{target_file}")
except Exception as e:
    print(f"[❌] 發生未知錯誤：{e}")
