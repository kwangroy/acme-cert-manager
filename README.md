# ACME certificate manager

通用的 ACME/Let's Encrypt 证书自动签发、续期与部署工具集，支持 Nginx、对象存储/CDN 证书同步，以及多域名、多服务器部署。

## 目录

- `src/`：可复用的 DNS、ACME/CDN 证书部署脚本
- `examples/main-domain/`：脱敏后的主域名 Nginx 和静态页示例
- `docs/`：通用部署与运维文档

## 安全边界

- 不要把 AccessKey、SecretKey、服务器密码、私钥、证书文件或运行日志提交到仓库。
- 脚本通过环境变量读取凭据；运行时证书目录应放在服务器的专用目录中，例如 `/opt/acme-cert-manager/`。
- 不要直接复制案例中的域名、服务器路径或 systemd 服务名到其他环境，先按目标环境修改配置。
- 本仓库不得出现真实域名、真实公网 IP、生产服务源码或现网配置；示例统一使用 `example.com` 和文档保留地址。
- 修改生产配置前先备份、执行配置检查，再 reload 服务。

部署流程与安全边界见 [`docs/deployment-ops-manual.md`](docs/deployment-ops-manual.md)。
