"""draw.io(mxGraph) XML 생성 헬퍼.

사용법 (생성 스크립트 안에서):
    import sys; sys.path.insert(0, "<skill>/scripts")
    from drawio_lib import *
    v("cf", "<b>CloudFront</b>", 400, 330, 64, 64, icon("cloudfront", C.NET))
    e("e1", "users", "cf", "HTTPS")
    save(sys.argv[1], page_w=1960, page_h=1160)

모든 셀은 parent="1"(루트)에 절대좌표로 둔다. 그룹 박스도 container=0 이라
안에 든 것처럼 '겹쳐 그리기'만 한다 — 좌표 계산이 단순하고 수정이 쉽다.
"""
from xml.sax.saxutils import escape

cells = []

FONT = "fontFamily=Noto Sans CJK KR;"


class C:
    """AWS 아키텍처 아이콘 공식 카테고리 색."""
    NET = "#8C4FFF"       # 네트워킹·CDN (CloudFront, Route 53, VPC, ELB)
    COMPUTE = "#ED7100"   # EC2, ECS, ECR, Lambda
    STORAGE = "#7AA116"   # S3, EBS, EFS
    DB = "#C925D1"        # RDS, DynamoDB, ElastiCache
    SECURITY = "#DD344C"  # IAM, WAF, ACM, Secrets Manager, KMS
    MGMT = "#E7157B"      # CloudWatch, SSM, SNS, SQS, EventBridge
    ANALYTICS = "#8C4FFF"
    DARK = "#232F3E"
    GRAY = "#666666"


def q(s):
    return escape(str(s), {'"': "&quot;"})


def v(id, label, x, y, w, h, style):
    """노드(vertex). label 은 html=1 이라 <b>, <br> 사용 가능."""
    cells.append(
        f'<mxCell id="{id}" value="{q(label)}" style="{q(style)}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


EDGE_BASE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;endFill=1;"
             "strokeWidth=1.5;fontSize=11;labelBackgroundColor=#FFFFFF;")
DASH = "dashed=1;"


def e(id, s, t, label="", style="", pts=None):
    """화살표. pts=[(x,y),...] 는 경유점(절대좌표).
    붙는 위치를 고정하려면 style 에 exitX/exitY/entryX/entryY (0~1) 를 준다."""
    geo = '<mxGeometry relative="1" as="geometry">'
    if pts:
        geo += '<Array as="points">' + "".join(f'<mxPoint x="{a}" y="{b}"/>' for a, b in pts) + "</Array>"
    geo += "</mxGeometry>"
    cells.append(
        f'<mxCell id="{id}" value="{q(label)}" style="{q(EDGE_BASE + style)}" edge="1" parent="1" '
        f'source="{s}" target="{t}">{geo}</mxCell>'
    )


def grp(icon, stroke, fill="none", fc=None, dashed=0):
    """AWS 그룹 박스 (group_aws_cloud_alt, group_region, group_vpc2, group_security_group,
    group_ec2_instance_contents, group_availability_zone, group_corporate_data_center ...)."""
    return (f"{FONT}points=[];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=13;fontStyle=1;"
            f"container=0;pointerEvents=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.{icon};"
            f"strokeColor={stroke};fillColor={fill};verticalAlign=top;align=left;spacingLeft=30;"
            f"fontColor={fc or stroke};dashed={dashed};")


def icon(res, color):
    """AWS 서비스 아이콘 (60x60 권장, 라벨은 아이콘 아래). res 이름은 references/aws-icons.md 참고."""
    return (f"{FONT}sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor={color};"
            f"strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;"
            f"fontSize=11;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};")


def person(shape="users"):
    """사람 아이콘: shape='users' | 'user'."""
    return (f"{FONT}sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#232F3D;"
            f"strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;"
            f"fontSize=11;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.{shape};")


def box(fill, stroke, fc="#232F3E", extra=""):
    """일반 둥근 박스 (파드·프로세스·외부 시스템)."""
    return f"{FONT}rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor={fc};fontSize=11;arcSize=12;{extra}"


def memo(fill="#FFF8E1", stroke="#F2C14E"):
    """좌측 정렬 메모 박스 (SG 규칙, 라우팅 규칙 같은 '그림으로 안 되는 설명')."""
    return box(fill, stroke, extra="align=left;spacingLeft=6;verticalAlign=top;")


def zone(fill="#EAF3FB", stroke="#147EBA"):
    """점선 영역 (k8s namespace, 논리 그룹)."""
    return (f"{FONT}rounded=1;dashed=1;fillColor={fill};strokeColor={stroke};fontColor={stroke};"
            f"verticalAlign=top;align=left;spacingLeft=8;fontStyle=1;fontSize=12;html=1;")


def cylinder(fill="#E1F5FE", stroke="#0277BD", fc="#01579B"):
    """DB 원통 (AWS 밖 DB 등)."""
    return (f"{FONT}shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;size=12;"
            f"fillColor={fill};strokeColor={stroke};fontColor={fc};fontSize=11;")


NOTE = f"{FONT}text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;fontSize=11;fontColor=#555555;"


def title(text, sub, x=40, y=10, w=900):
    v("title", f"<b style='font-size:22px'>{text}</b><br><span style='font-size:12px;color:#666'>{sub}</span>",
      x, y, w, 50, f"{FONT}text;html=1;align=left;verticalAlign=top;")


def save(out, page_w=1960, page_h=1160, name="Infra"):
    """그룹 박스가 먼저 그려져야 뒤에 깔리므로, 그룹 v() 를 노드보다 먼저 호출할 것."""
    xml = (f'<mxfile host="drawio"><diagram id="infra" name="{q(name)}">'
           f'<mxGraphModel dx="{page_w}" dy="{page_h}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
           f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_w}" pageHeight="{page_h}" '
           f'background="#FFFFFF" math="0" shadow="0">'
           '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram></mxfile>")
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"wrote {out} ({len(cells)} cells)")
