
- 3389_fofa_shodan.py


填入 Shodan / Fofa apikey 以及 gmail，新建目標 targets.txt 與 3389_fofa_shodan.py 放在同一目錄下(ip 格式如 8.8.8.8 無任何 http or https 路徑)，會針對 IP 進行比對(Fofa/Shodan) 都存在 3389 端口是否存在，最後會將兩者都有 3389 端口的 IP 存為 final_rdp.txt。

