import shodan

# 替換為您的 Shodan API 密鑰
API_KEY = 'YOUR_SHODAN_API_KEY'

# 初始化 Shodan 客戶端
api = shodan.Shodan(API_KEY)

# 載入目標 IP 清單的文件名稱
target_file = 'targets.txt'
# 保存有開啟 3389 的 IP 的文件
output_file = '200_rdp.txt'

try:
    with open(target_file, 'r') as f:
        target_ips = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(target_ips)} target IPs from {target_file}")

    open_rdp_ips = []

    for ip in target_ips:
        try:
            print(f"Checking IP: {ip}")
            host = api.host(ip)

            # 檢查是否開啟 3389 服務
            if any(service['port'] == 3389 for service in host.get('data', [])):
                print(f"[+] {ip} has port 3389 open!")
                open_rdp_ips.append(ip)
                if 'hostnames' in host and host['hostnames']:
                    print(f"Hostnames: {', '.join(host['hostnames'])}")
                if 'location' in host and host['location']:
                    location = host['location']
                    print(f"Location: {location.get('city', 'Unknown')}, {location.get('country_name', 'Unknown')}")
            else:
                print(f"[-] {ip} does not have port 3389 open.")

            print("-" * 40)
        except shodan.APIError as e:
            print(f"Error checking IP {ip}: {e}")

    # 保存有開啟 3389 的 IP 到文件
    with open(output_file, 'w') as f:
        f.write("\n".join(open_rdp_ips))
    print(f"Saved {len(open_rdp_ips)} IPs with port 3389 open to {output_file}")

except FileNotFoundError:
    print(f"Error: File {target_file} not found.")
except shodan.APIError as e:
    print(f"Shodan API Error: {e}")
