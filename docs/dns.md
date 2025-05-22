Некоторые сервисы блокируются не Роскомнадзором (через ТСПУ), а напрямую самим сайтом.

То есть сам сайт (ChatGPT, Gemini и т.д.) запрещает чтобы на него заходили из под РФ айпишников. Zapret не меняет IP адрес, поэтому использовать его для обхода GEO блокировок бесполезно. Вам следует либо поменять DNS в браузере, либо использовать встроенную функцию разблокировки hosts в Zapret GUI.

## Список DSN
### XBOX DNS
```
176.99.11.77
```
```
80.78.247.254
```

HTTPS:
```
https://xbox-dns.ru/dns-query
```
TLS:
```
xbox-dns.ru
```

### Comss DNS
https://www.comss.ru/page.php?id=7315

DNS-over-HTTPS (DoH) – Windows, Браузеры
```
https://dns.comss.one/dns-query
```
DNS-over-HTTPS (DoH) – iPhone, iPad, Mac
```
dns.comss.one.mobileconfig
```
DNS-over-TLS (DoT) – Android, Linux

`dns.comss.one` или `tls://dns.comss.one`

DNS-over-QUIC (DoQ)
```
quic://dns.comss.one
```
