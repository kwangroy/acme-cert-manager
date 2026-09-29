# ACME 证书自动签发与部署手册

本手册是通用模板，不包含任何真实域名、服务器地址、密钥或生产配置。部署到新环境前，必须替换所有 `example.com`、示例 IP、服务名和目录。

## 1. 架构原则

- ACME 客户端负责向证书颁发机构申请和续期证书。
- 主域名证书可覆盖主域名和普通一级子域名，例如 `example.com`、`www.example.com`。
- 泛域名证书只覆盖一级子域名，不覆盖 `a.b.example.com`。
- 对旧客户端、CDN 或不同信任边界，使用独立证书，减少单个私钥泄露的影响范围。
- 原有 Certbot 管理的证书不要擅自迁移；迁移前必须确认服务、证书路径和续期任务的归属。

## 2. 推荐目录

```text
/opt/acme-cert-manager/
├── acme/                         # ACME 客户端程序
├── acme-data/                    # ACME 账户、订单和状态
├── bin/                          # 部署脚本
├── certs/                        # 证书和私钥，仅 root 可读
├── config/                       # 非敏感配置
├── logs/                         # 运行日志
└── secrets/
    └── provider.env              # DNS/CDN 凭据，root:root，权限 600
```

证书私钥、DNS/CDN 密钥、服务器密码、真实域名和公网 IP 不得进入 Git 仓库。仓库只保存脚本、脱敏模板和操作说明。

## 3. 证书规划示例

```text
example.com + *.example.com       主站和普通一级子域名
transfer.example.com               旧客户端专用 RSA 证书
media.example.com                  CDN 独立证书
qr.example.com                     CDN 独立证书
auth.example.com                   原有 Certbot 管理，保持不迁移
data.example.com                   原有 Certbot 管理，保持不迁移
```

证书类型必须与实际客户端兼容；不能仅因为证书都是 Let’s Encrypt，就假定所有客户端行为完全一致。

## 4. 凭据与权限

```bash
sudo install -d -m 0700 -o root -g root /opt/acme-cert-manager/secrets
sudo install -m 0600 -o root -g root provider.env \
  /opt/acme-cert-manager/secrets/provider.env
```

禁止把 `provider.env`、`privkey.pem`、访问令牌或云厂商密钥放到网站目录、Git 工作区或聊天记录中。

## 5. Nginx 部署原则

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name example.com;

    root /var/www/example.com/public;
    ssl_certificate /opt/acme-cert-manager/certs/example.com/fullchain.pem;
    ssl_certificate_key /opt/acme-cert-manager/certs/example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
}
```

修改后先检查，再 reload：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

证书目录不能位于 `/var/www` 或其他可被 Web 服务直接访问的目录；Nginx 只应读取证书，不应暴露私钥文件。

## 6. 续期任务

systemd timer 只是调度器，实际执行者可以是 Certbot 或 acme.sh。一个证书只能由一个明确的续期任务管理，避免 Certbot 和 acme.sh 同时申请、覆盖同一证书。

```bash
sudo systemctl list-timers --all | grep -Ei 'certbot|acme|cert'
sudo systemctl status acme-cert-renew.timer
sudo journalctl -u acme-cert-renew.service -n 100 --no-pager
```

续期成功后必须执行对应的部署动作，例如 reload Nginx 或更新 CDN 证书。

## 7. DNS/CDN 部署

- DNS API 账号只授予目标域名的 DNS 记录权限。
- CDN 账号只授予证书上传和目标域名绑定权限。
- 证书上传时使用 `fullchain.pem` 和对应的 `privkey.pem`。
- CDN 证书与源站证书可以分开签发，降低私钥泄露影响范围。
- 每次更新后检查 CDN 实际返回的证书，不要只检查源站文件。

## 8. 验证与故障排查

```bash
echo | openssl s_client \
  -connect example.com:443 \
  -servername example.com 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

重点检查：DNS、443 的 `server_name`、`fullchain.pem`、证书 SAN、证书与私钥匹配、CDN 传播，以及是否有重复续期任务。

## 9. 禁止事项

- 不提交真实域名、真实 IP、私钥、云密钥、服务器密码或生产日志。
- 不删除其他服务正在使用的 Certbot 证书和续期任务。
- 不跳过备份、`nginx -t` 和 reload 验证直接修改生产配置。
- 不把证书管理目录映射到 Web 根目录。
- 不把真实现网配置作为通用示例提交到公共仓库。
