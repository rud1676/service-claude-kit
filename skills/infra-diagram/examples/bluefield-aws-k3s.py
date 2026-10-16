"""예시: BlueField live 인프라 (AWS CloudFront + EC2 k3s 단일 노드 + 외부 DB).
실행: python3 bluefield-aws-k3s.py out.drawio && ../scripts/render.sh out.drawio
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from drawio_lib import *  # noqa

# ---------- title ----------
v("title", "<b style='font-size:22px'>BlueField 인프라 구성도</b><br><span style='font-size:12px;color:#666'>live 환경 · repository/infra (terraform + kube) 기준 · 2026-10-13</span>",
  40, 10, 700, 50, f"{FONT}text;html=1;align=left;verticalAlign=top;")

# ---------- groups (background) ----------
v("g_aws", "AWS Cloud (계정 BlueField)", 290, 80, 1450, 1060, grp("group_aws_cloud_alt", "#232F3E"))
v("g_edge", "Global · us-east-1 (Edge)", 310, 120, 450, 640, grp("group_region", "#8C4FFF", fc="#8C4FFF", dashed=1))
v("g_region", "ap-northeast-2 (서울)", 790, 120, 930, 1000, grp("group_region", "#00A4A6", fc="#147EBA", dashed=1))
v("g_vpc", "VPC 10.0.0.0/16  (IGW · 퍼블릭 서브넷 a/c, NAT 없음)", 810, 160, 640, 600, grp("group_vpc2", "#8C4FFF", fc="#8C4FFF"))
v("g_subnet", "Public subnet a · 10.0.1.0/24", 830, 200, 600, 545, grp("group_security_group", "#7AA116", fill="#F2F6E8", fc="#248814"))
v("g_ec2", "EC2 t3.medium · k3s 단일 노드  (gp3 30GB · cpu_credits=standard)", 850, 240, 560, 490, grp("group_ec2_instance_contents", "#D86613", fill="#FFFFFF", fc="#D86613"))
v("g_ns", "namespace: live", 1060, 300, 330, 230, f"{FONT}rounded=1;dashed=1;fillColor=#EAF3FB;strokeColor=#147EBA;fontColor=#147EBA;verticalAlign=top;align=left;spacingLeft=8;fontStyle=1;fontSize=12;html=1;")
v("sg_note", "<b>SG blue-field-k3s-node</b><br>443 ← CloudFront prefix list<br>80 ← 0.0.0.0/0 (ACME 검증)<br>6443 ← 작업 서버 IP<br>22 없음 (SSM 사용)<br><b>EIP</b> 43.203.16.98",
  868, 380, 170, 110, box("#FFF8E1", "#F2C14E", extra="align=left;spacingLeft=6;verticalAlign=top;"))

# ---------- left: actors ----------
U = f"{FONT}sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#232F3D;strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=11;aspect=fixed;pointerEvents=1;"
v("users", "<b>사용자 브라우저</b><br>blfil.com", 115, 270, 60, 60, U + "shape=mxgraph.aws4.users;")
v("adminuser", "<b>운영자</b><br>admin.blfil.com<br>(허용 IP에서만)", 120, 470, 50, 50, U + "shape=mxgraph.aws4.user;")
v("operator", "<b>작업 서버</b> (operator_cidr)<br>kubectl · SSM 세션", 40, 640, 210, 50, box("#F5F5F5", "#666666"))
v("github", "<b>GitHub Actions</b><br>live-release.yml (stage 수동 실행)<br>server · front · admin repo", 40, 860, 210, 70, box("#24292F", "#24292F", fc="#FFFFFF"))
v("le", "<b>Let's Encrypt</b><br>HTTP-01 검증", 40, 760, 210, 44, box("#F5F5F5", "#666666"))

# ---------- edge ----------
v("r53", "<b>Route 53</b><br>blfil.com 호스팅존<br>(data로 조회만)", 345, 165, 60, 60, icon("route_53", "#8C4FFF"))
v("acm", "<b>ACM</b><br>blfil.com·www·admin", 530, 165, 60, 60, icon("certificate_manager_3", "#DD344C"))
v("cf_front", "<b>CloudFront (front)</b><br>blfil.com · www<br>PriceClass_200", 400, 330, 64, 64, icon("cloudfront", "#8C4FFF"))
v("cf_admin", "<b>CloudFront (admin)</b><br>admin.blfil.com", 400, 520, 64, 64, icon("cloudfront", "#8C4FFF"))
v("waf", "<b>WAF</b><br>admin IP 허용목록<br>그 외 403", 640, 445, 60, 60, icon("waf", "#DD344C"))
v("cff_note", "<b>경로 라우팅 (두 배포 공통)</b><br>/api/* → api-origin (캐시 X)<br>정적(/_next/static, /assets) → 캐시<br>나머지(SSR·index) → 앱 오리진<br>/maintenance.html → S3<br><b>CF Function</b>: www→301, 점검 시 302",
  555, 290, 200, 130, box("#F3EEFF", "#8C4FFF", extra="align=left;spacingLeft=6;verticalAlign=top;"))
v("dns_note", "*-origin.blfil.com (front/api/admin)<br>A 레코드 → EIP", 500, 640, 240, 40, NOTE)

# ---------- k3s node internals ----------
v("traefik", "<b>Traefik Ingress</b><br>websecure :443 전용<br>Host로 서비스 선택", 870, 300, 170, 60, box("#FCE4D6", "#D86613"))
P = box("#FFFFFF", "#147EBA")
v("p_front", "<b>bf-front</b><br>Next.js SSR", 1075, 330, 140, 44, P)
v("p_admin", "<b>bf-admin</b><br>Vite SPA", 1235, 330, 140, 44, P)
v("p_api", "<b>bf-api</b><br>NestJS api_server", 1075, 400, 140, 44, P)
v("p_batch", "<b>bf-batch</b><br>NestJS batch_server", 1235, 400, 140, 44, P)
v("p_migrate", "<b>migrate Job</b><br>prisma migrate", 1235, 470, 140, 44, box("#FFFFFF", "#147EBA", extra="dashed=1;"))
v("certm", "<b>cert-manager</b><br>ClusterIssuer letsencrypt-prod", 870, 560, 170, 50, box("#FCE4D6", "#D86613"))
v("eso", "<b>External Secrets</b><br>→ Secret bf-api-secret", 1060, 560, 160, 50, box("#FCE4D6", "#D86613"))
v("cwa", "<b>CloudWatch Agent</b><br>mem · disk 수집", 1235, 560, 150, 50, box("#FCE4D6", "#D86613"))
v("imds_note", "앱의 AWS 접근 = 노드 IAM 역할 (IMDSv2, hop 2) · 액세스 키 없음", 870, 650, 520, 30, NOTE + "fontColor=#D86613;")

# ---------- regional services ----------
v("s3prod", "<b>S3 bluefield-prod</b><br>앱 이미지 업로드", 1590, 170, 60, 60, icon("s3", "#7AA116"))
v("ses", "<b>SES</b><br>no-reply@blfil.com<br>DKIM·MAIL FROM·DMARC", 1590, 300, 60, 60, icon("simple_email_service", "#DD344C"))
v("cw", "<b>CloudWatch 알람</b><br>CPU·크레딧·메모리<br>디스크·상태검사", 1590, 520, 60, 60, icon("cloudwatch_2", "#E7157B"))
v("sns", "<b>SNS</b><br>blue-field-alerts → 이메일", 1590, 690, 60, 60, icon("sns", "#E7157B"))
v("s3maint", "<b>S3 maintenance</b><br>점검 페이지 (OAC 전용)", 840, 860, 60, 60, icon("s3", "#7AA116"))
v("ecr", "<b>ECR × 4</b><br>api-server · batch-server<br>front · admin (live-&lt;sha&gt;)", 1010, 860, 60, 60, icon("ecr", "#ED7100"))
v("ps", "<b>Parameter Store</b><br>/blue-field/live/api/*", 1180, 860, 60, 60, icon("systems_manager", "#E7157B"))
v("ssm", "<b>Systems Manager</b><br>Session Manager<br>SendCommand", 1340, 860, 60, 60, icon("systems_manager", "#E7157B"))
v("iam", "<b>IAM</b><br>GitHub OIDC<br>live-release 역할<br>(stage ref만 신뢰)", 1540, 860, 60, 60, icon("identity_and_access_management", "#DD344C"))

# ---------- external ----------
v("gabia", "<b>가비아 PostgreSQL 11</b><br>(AWS 밖 · DB 호스팅)", 1770, 420, 150, 80,
  f"{FONT}shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;size=12;fillColor=#E1F5FE;strokeColor=#0277BD;fontColor=#01579B;fontSize=11;")
v("mail", "알람 수신 이메일", 1770, 700, 150, 40, box("#F5F5F5", "#666666"))

# ---------- edges ----------
DASH = "dashed=1;"
e("e1", "users", "r53", "DNS", DASH + "strokeColor=#8C4FFF;", pts=[(145, 195)])
e("e2", "users", "cf_front", "HTTPS", "strokeColor=#232F3E;")
e("e3", "adminuser", "cf_admin", "HTTPS", "strokeColor=#232F3E;", pts=[(300, 495), (300, 552)])
e("e4", "waf", "cf_admin", "web ACL", DASH + "strokeColor=#DD344C;endArrow=none;exitX=0;exitY=0.5;entryX=0.5;entryY=0;", pts=[(432, 475)])
e("e5", "acm", "cf_front", "인증서", DASH + "strokeColor=#DD344C;", pts=[(560, 280), (432, 280)])
e("e6", "cf_front", "traefik", "front-origin · api-origin :443", "strokeColor=#8C4FFF;strokeWidth=2;exitX=1;exitY=0.25;", pts=[(520, 346), (520, 270), (955, 270)])
e("e7", "cf_admin", "traefik", "admin-origin · api-origin :443", "strokeColor=#8C4FFF;strokeWidth=2;", pts=[(780, 552), (780, 345)])
e("e8", "cf_front", "s3maint", "", DASH + "strokeColor=#7AA116;exitX=0;exitY=0.75;entryX=0.67;entryY=0;", pts=[(380, 378), (380, 780), (880, 780)])
e("e9", "cf_admin", "s3maint", "/maintenance.html", DASH + "strokeColor=#7AA116;exitX=0;exitY=0.5;entryX=0.33;entryY=0;", pts=[(370, 552), (370, 800), (860, 800)])
e("e10", "traefik", "p_front", "", "strokeColor=#D86613;", pts=[(1055, 330), (1055, 352)])
e("e11", "traefik", "p_api", "", "strokeColor=#D86613;", pts=[(1055, 345), (1055, 422)])
e("e12", "traefik", "p_admin", "", "strokeColor=#D86613;exitX=0.5;exitY=0;", pts=[(955, 290), (1305, 290)])
e("e13", "p_api", "gabia", "Prisma", "strokeColor=#0277BD;strokeWidth=2;exitX=0.5;exitY=1;", pts=[(1145, 470), (1745, 470)])
e("e14", "p_batch", "gabia", "", "strokeColor=#0277BD;strokeWidth=2;")
e("e15", "p_api", "s3prod", "업로드", DASH + "strokeColor=#7AA116;exitX=0.25;exitY=0;", pts=[(1110, 285), (1500, 285), (1500, 200)])
e("e16", "p_api", "ses", "인증·재설정 메일", DASH + "strokeColor=#DD344C;exitX=0.75;exitY=0;", pts=[(1180, 315), (1520, 315), (1520, 330)])
e("e17", "eso", "ps", "GetParameters", DASH + "strokeColor=#E7157B;")
e("e18", "g_ec2", "ecr", "image pull", DASH + "strokeColor=#ED7100;exitX=0.29;exitY=1;", pts=[(1012, 800), (1040, 800)])
e("e19", "cwa", "cw", "지표", DASH + "strokeColor=#E7157B;", pts=[(1310, 630), (1560, 630), (1560, 550)])
e("e20", "cw", "sns", "", "strokeColor=#E7157B;exitX=1;exitY=0.5;entryX=1;entryY=0.2;", pts=[(1700, 550), (1700, 702)])
e("e21", "sns", "mail", "", "strokeColor=#E7157B;exitX=1;exitY=0.65;entryX=0;entryY=0.5;")
e("e22", "github", "iam", "① OIDC AssumeRole", "strokeColor=#24292F;exitX=0.5;exitY=1;entryX=1;entryY=0.5;", pts=[(145, 1090), (1700, 1090), (1700, 890)])
e("e23", "github", "ecr", "② docker push", "strokeColor=#24292F;exitX=1;exitY=0.75;", pts=[(1040, 912)])
e("e24", "github", "ssm", "③ SendCommand", "strokeColor=#24292F;exitX=0.75;exitY=1;entryX=0;entryY=0.5;", pts=[(197, 1040), (1300, 1040), (1300, 890)])
e("e25", "ssm", "g_ec2", "kubectl set image → rollout", "strokeColor=#E7157B;exitX=0.5;exitY=0;entryX=0.95;entryY=1;", pts=[(1370, 790), (1382, 790)])
e("e26", "operator", "g_ec2", "kubectl :6443", "strokeColor=#666666;", pts=[(280, 665), (280, 720), (850, 720)])
e("e27", "le", "certm", ":80 HTTP-01", DASH + "strokeColor=#666666;", pts=[(270, 782), (270, 740), (820, 740), (820, 585)])

save(sys.argv[1], page_w=1960, page_h=1160, name="BlueField infra")
