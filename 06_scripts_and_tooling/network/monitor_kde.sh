#!/bin/bash
echo "Starting continuous KDE Connect monitor (ignoring all Mac/Pixel/known IPs)..."
while true; do
    # Scan for KDE Connect TCP port
    output=$(nmap -p 1716 --open 192.168.8.0/24 -T4 -oG - | awk '/1716\/open/{print $2}')
    
    for ip in $output; do
        banner=$(nc -v -w 2 $ip 22 2>&1 | grep "OpenSSH")
        if [[ ! "$ip" =~ ^(192\.168\.8\.143|192\.168\.8\.230|192\.168\.8\.127|192\.168\.8\.245|192\.168\.8\.226|192\.168\.8\.213)$ ]] && [[ ! "$banner" =~ "OpenSSH_10.3" ]]; then
            echo "NEW KDE CONNECT DEVICE FOUND AT: $ip"
            # Do a quick SSH scan on it
            nmap -p 22,8022,2022 -Pn $ip
            exit 0
        fi
    done
    sleep 10
done
