
- 3389_fofa_shodan.py


填入 Shodan / Fofa apikey 以及 Gmail，新建目標 targets.txt 與 3389_fofa_shodan.py 放在同一目錄下

ip 格式如 8.8.8.8，針對 IP 進行比對(Fofa/Shodan)，最後會將兩者都有 3389 端口的 IP 存為 final_rdp.txt。

- Scan_Web_Shodan_API_Thread

針對單個 IP 或多個掃描 > 結果存在 DeBug/log.xlsx，內容包含 : 掃描時間、目標IP、HTTP 標題。
