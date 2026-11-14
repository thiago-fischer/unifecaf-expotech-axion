# Laboratório de rede do Axion

O painel Rede exibe metadados sanitizados observados no namespace do backend.
Ele não armazena PCAP, payloads, cabeçalhos HTTP, comandos SQL, credenciais ou
identificadores RFID obtidos de corpos de requisição.

A captura cobre o tráfego do frontend para o backend e as conexões do backend
com o controlador e o PostgreSQL. O tráfego Grafana → PostgreSQL aparece como
conexão configurada, pois não atravessa o namespace capturado.

O ambiente usa HTTP na rede Docker local. A captura não representa teste de
hardware, Wi-Fi, IDS, SIEM ou garantia de confidencialidade.
