import json
import os
import sys

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import matplotlib.transforms as transforms
    from matplotlib import font_manager, rc
except ImportError:
    print("matplotlib 라이브러리가 필요합니다. 'pip install matplotlib'을 실행해주세요.")
    sys.exit(1)

def draw_blueprint():
    # 한글 폰트 설정
    font_path = "C:/Windows/Fonts/malgun.ttf"
    if os.path.exists(font_path):
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        rc('font', family=font_name)
    else:
        rc('font', family='AppleGothic')
    plt.rcParams['axes.unicode_minus'] = False

    # 데이터 로드
    directory = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(directory, 'layout_data.json')
    
    if not os.path.exists(json_path):
        print(f"데이터 파일이 없습니다: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 열람실 영역 정보
    room = data.get('room', {})
    rw = room.get('w', 1000)
    rh = room.get('h', 800)
    
    # 전체 요소 리스트
    elements = data.get('elements', [])
    
    fig, ax = plt.subplots(figsize=(16, 10))

    # 1. 열람실 영역 그리기 (원점 0,0 기준)
    ax.add_patch(patches.Rectangle((0, 0), rw, rh, linewidth=3, edgecolor='#2c3e50', facecolor='none', zorder=1))
    
    # 2. 모든 객체 그리기 (데이터의 x, y를 그대로 사용)
    colors = {
        'seat': '#d1f2eb', 'motion': '#fcf3cf', 'door': '#f5b7b1', 
        'window': '#a3e4d7', 'pillar': '#aeb6bf', 'wall': '#d5dbdb'
    }
    edge_colors = {
        'seat': '#1abc9c', 'motion': '#f39c12', 'door': '#e74c3c', 
        'window': '#16a085', 'pillar': '#34495e', 'wall': '#7f8c8d'
    }

    for el in elements:
        cat = el.get('category')
        x, y, w, h = el.get('x', 0), el.get('y', 0), el.get('w', 30), el.get('h', 30)
        r = el.get('r', 0)
        item_id = str(el.get('id', ''))
        
        # 회전 중심점
        cx, cy = x + w/2, y + h/2
        fc = colors.get(cat, '#eeeeee')
        ec = edge_colors.get(cat, '#333333')
        
        if cat == 'seat':
            s_type = el.get('type', 'normal')
            if s_type == 'cubicle': fc = '#a9cce3'
            elif s_type == 'disabled': fc = '#d7bde2'

        rect = patches.Rectangle((x, y), w, h, linewidth=1.5, edgecolor=ec, facecolor=fc, zorder=2)
        # 회전 변환 적용
        t = transforms.Affine2D().rotate_deg_around(cx, cy, r) + ax.transData
        rect.set_transform(t)
        ax.add_patch(rect)
        
        # ID 텍스트 (회전 안 함)
        if item_id:
            ax.text(cx, cy, item_id, ha='center', va='center', fontsize=8, fontweight='bold', zorder=3)

    # 축 설정
    ax.set_xlim(-50, rw + 50)
    ax.set_ylim(-50, rh + 50)
    ax.set_aspect('equal')
    ax.invert_yaxis() # 그래픽 좌표계 (Y축 아래로 증가)
    ax.axis('off')

    plt.title("열람실 배치도", fontsize=22, fontweight='bold', pad=20, color='#2c3e50')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    draw_blueprint()
