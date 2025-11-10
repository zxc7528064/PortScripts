<#
  Low-noise Multi-Subnet TCP Port Scanner (UTF-8)
  - Based on your original script, modified to reduce scan "burstiness" and patternability.
  - Strategies:
    * Ping prefilter (fallback to lightweight TCP probe if ICMP blocked)
    * Randomize order of hosts and ports
    * Prioritize first-ports (80/443/3389) to reduce total probes when quick intel needed
    * Per-connection jitter and batch sleeps
    * Exponential backoff for repeatedly failing hosts
    * Synchronous (single-threaded) loop for minimal parallel noise (compatible with PS5.1/PS7)
  Usage:
    - Edit $subnets / $ports as needed, then run.
  WARNING: Run only on authorized targets.
#>

# === User Config ===
$subnets = @(
    "128.1.50.0/24",
    "128.1.120.0/24",
    "128.1.10.0/24",
    "128.1.140.0/24",
    "172.26.1.0/24",
    "128.1.60.0/24",
    "128.3.50.0/24",
    "128.1.40.0/24",
    "128.1.30.0/24",
    "128.1.130.0/24"
)

# full ports list (you provided)
$ports       = @(21,22,80,443,1433,3389,6379,8080,8089)

# output
$outputFile  = ".\scan_open_multi_subnets_lownoise.csv"

# timing / noise-control params (tune conservatively)
$timeoutMs        = 1200   # connect timeout per attempt (ms)
$pingTimeoutMs    = 450    # ICMP ping timeout (ms)
$usePingPrefilter = $true  # if $true try ping first; if ping blocked, fallback to TCP probe
$jitterMinMs      = 60     # per-connection random sleep min (ms)
$jitterMaxMs      = 220    # per-connection random sleep max (ms)
$batchSize        = 150    # number of (host:port) attempts per batch before longer sleep
$batchSleepMs     = 3000   # sleep between batches (ms)
$perHostBackoffBaseMs = 1000 # base backoff for failed hosts (ms); backoff grows exponentially
$maxBackoffAttempts = 4    # after this many failures skip further scanning for that host
$firstPorts       = @(80,443,3389) # scanned first for quicker useful results
# ===================


# write header (overwrite)
"IP,Port,Status,Time" | Out-File -Encoding utf8 -FilePath $outputFile


# ---------- helpers ----------
function Get-SubnetHostsFromCidr {
    param([Parameter(Mandatory = $true)][string]$cidr)
    if ($cidr -notmatch '^([\d\.]+)/(\d{1,2})$') { throw "Invalid CIDR format: $cidr" }
    $base = $matches[1]; $mask = [int]$matches[2]
    $bytes = [System.Net.IPAddress]::Parse($base).GetAddressBytes(); [array]::Reverse($bytes)
    $baseInt = [BitConverter]::ToUInt32($bytes,0); $hostBits = 32 - $mask

    if ($hostBits -ge 2) {
        $hostCount = [int]([math]::Pow(2,$hostBits) - 2)
        $start = $baseInt + 1; $end = $baseInt + $hostCount
    } elseif ($hostBits -eq 1) {
        $start = $baseInt; $end = $baseInt + 1
    } else {
        $start = $baseInt; $end = $baseInt
    }

    $list = New-Object System.Collections.Generic.List[string]
    for ($i = $start; $i -le $end; $i++) {
        $b = [BitConverter]::GetBytes([uint32]$i); [array]::Reverse($b)
        $list.Add(([System.Net.IPAddress]::new($b)).ToString())
    }
    return $list
}

function Test-HostAlive {
    param([string]$ip, [int]$timeoutMs = 500)
    try {
        $ping = New-Object System.Net.NetworkInformation.Ping
        $reply = $ping.Send($ip, $timeoutMs)
        return $reply.Status -eq 'Success'
    } catch { return $false }
}

function TcpProbe {
    param([string]$ip, [int]$port = 80, [int]$timeoutMs = 700)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $task = $tcp.ConnectAsync($ip, $port)
        if ($task.Wait($timeoutMs)) {
            if ($tcp.Connected) { $tcp.Close(); return $true }
        }
        $tcp.Close()
        return $false
    } catch { return $false }
}

function TcpConnectWithTimeout {
    param([string]$ip, [int]$port, [int]$timeoutMs)
    # returns $true if connected, $false otherwise
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect($ip, $port, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne($timeoutMs, $false)
        if ($wait) {
            try { $tcp.EndConnect($iar) } catch {}
        }
        $connected = $tcp.Connected
        if ($tcp -ne $null) { try { $tcp.Close() } catch {} }
        return $connected
    } catch { return $false }
}

function RandomSleep {
    param([int]$minMs, [int]$maxMs)
    $r = Get-Random -Minimum $minMs -Maximum ($maxMs + 1)
    Start-Sleep -Milliseconds $r
}

# ---------- build target lists ----------
$total = 0
$subnetHostsMap = @{}

foreach ($cidr in $subnets) {
    try {
        $hosts = Get-SubnetHostsFromCidr -cidr $cidr
        $subnetHostsMap[$cidr] = $hosts
        $total += ($hosts.Count * $ports.Count)
    } catch {
        Write-Warning "Failed to parse subnet: $cidr - $_"
        $subnetHostsMap[$cidr] = @()
    }
}

if ($total -eq 0) {
    Write-Host "No valid hosts to scan. Exiting."
    return
}

# ---------- main low-noise scanning ----------
$counter = 0
$batchCounter = 0

# per-host failure counter for backoff
$hostFailCount = @{}

foreach ($cidr in $subnets) {
    $hosts = $subnetHostsMap[$cidr]
    if ($hosts.Count -eq 0) { continue }

    # randomize host order to remove sequential pattern
    $hosts = $hosts | Get-Random -Count $hosts.Count

    # build per-subnet port order: firstPorts first (if present), then remaining randomized
    $otherPorts = $ports | Where-Object { $firstPorts -notcontains $_ } | Get-Random -Count ( ($ports | Where-Object { $firstPorts -notcontains $_ }).Count )
    $portOrder = @($firstPorts + $otherPorts) | Where-Object { $ports -contains $_ } # keep only ports in $ports

    $subTotal = $hosts.Count * $portOrder.Count
    $subCounter = 0

    foreach ($ip in $hosts) {
        # skip if host has exceeded backoff attempts
        if ($hostFailCount.ContainsKey($ip) -and $hostFailCount[$ip] -ge $maxBackoffAttempts) {
            # skip scanning this host further (to reduce noise for likely-dead hosts)
            continue
        }

        # Host alive check (ping preferred)
        $alive = $false
        if ($usePingPrefilter) {
            $alive = Test-HostAlive -ip $ip -timeoutMs $pingTimeoutMs
            if (-not $alive) {
                # fallback to small TCP probe on port 80 if ping blocked
                $alive = TcpProbe -ip $ip -port 80 -timeoutMs 700
            }
        } else {
            # direct lightweight probe if ping not used
            $alive = TcpProbe -ip $ip -port 80 -timeoutMs 700
        }

        if (-not $alive) {
            # increment fail counter and skip heavy port scanning for now
            if (-not $hostFailCount.ContainsKey($ip)) { $hostFailCount[$ip] = 0 }
            $hostFailCount[$ip]++
            # small randomized quiet delay to avoid immediate next host pattern
            RandomSleep -minMs $jitterMinMs -maxMs $jitterMaxMs
            continue
        } else {
            # reset fail count on success
            if ($hostFailCount.ContainsKey($ip)) { $hostFailCount[$ip] = 0 }
        }

        # scan ports in randomized/prioritized order
        foreach ($port in $portOrder) {
            $counter++; $subCounter++; $batchCounter++

            $overallPercent = [int](($counter / $total) * 100)
            $subPercent     = [int](($subCounter / $subTotal) * 100)

            Write-Progress -Id 1 -Activity "Overall Progress" -Status "Subnet $cidr — $counter / $total" -PercentComplete $overallPercent
            Write-Progress -Id 2 -Activity "Scanning: $cidr" -Status "$ip : $port ($subCounter / $subTotal)" -PercentComplete $subPercent

            # per-connection small random sleep (jitter) to avoid uniform timing
            RandomSleep -minMs $jitterMinMs -maxMs $jitterMaxMs

            $ok = TcpConnectWithTimeout -ip $ip -port $port -timeoutMs $timeoutMs
            if ($ok) {
                $ts = (Get-Date).ToString("o")
                "$ip,$port,Open,$ts" | Out-File -Append -Encoding utf8 -FilePath $outputFile
                Write-Host "[+] $ip : $port Open"
                # if open is found, reset host failure counter
                if ($hostFailCount.ContainsKey($ip)) { $hostFailCount[$ip] = 0 }
            } else {
                # increment host fail count moderately (failure per port)
                if (-not $hostFailCount.ContainsKey($ip)) { $hostFailCount[$ip] = 0 }
                $hostFailCount[$ip]++
            }

            # exponential backoff if host fails repeatedly
            if ($hostFailCount[$ip] -gt 0) {
                $attempts = [int]$hostFailCount[$ip]
                if ($attempts -gt 1) {
                    $backoffMs = [math]::Min($perHostBackoffBaseMs * [math]::Pow(2, $attempts - 1), 30000)
                    Start-Sleep -Milliseconds $backoffMs
                }
            }

            # batch sleep control (reduce traffic spikes)
            if ($batchCounter -ge $batchSize) {
                $batchCounter = 0
                Start-Sleep -Milliseconds $batchSleepMs
            }
        } # end port loop
    } # end host loop

    Write-Progress -Id 2 -Activity "Scanning: $cidr" -Status "Completed" -PercentComplete 100
} # end cidr loop

# finalize
Write-Progress -Id 1 -Activity "Overall Progress" -Completed
Write-Progress -Id 2 -Activity "Scanning" -Completed
Write-Host ""
Write-Host "✅ Low-noise scan completed. Open ports saved to $outputFile"
