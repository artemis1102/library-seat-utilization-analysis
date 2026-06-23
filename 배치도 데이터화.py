import http.server
import socketserver
import json
import os
import webbrowser
import threading
import socket

DIRECTORY = os.path.dirname(os.path.abspath(__file__))

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>열람실 배치도 에디터</title>
    <style>
        body { margin: 0; font-family: 'Malgun Gothic', sans-serif; display: flex; height: 100vh; overflow: hidden; background: #f0f0f0; }
        #toolbar { width: 250px; background: #2c3e50; color: white; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; z-index: 10; box-shadow: 2px 0 5px rgba(0,0,0,0.1); }
        #toolbar h2 { margin-top: 0; font-size: 18px; border-bottom: 1px solid #455a64; padding-bottom: 10px; }
        .tool-btn { background: #34495e; color: white; border: 1px solid #2c3e50; padding: 12px; margin-bottom: 8px; cursor: pointer; text-align: left; border-radius: 4px; transition: 0.2s; }
        .tool-btn:hover { background: #465c72; }
        .tool-btn.active { background: #3498db; border-color: #2980b9; font-weight: bold; }
        
        #workspace { flex-grow: 1; overflow: auto; position: relative; background: #dcdde1; }
        #canvas-container { position: relative; display: inline-block; transform-origin: top left; margin: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.2); background: white;}
        #bg-image { display: block; max-width: none; }
        
        .element { position: absolute; box-sizing: border-box; cursor: pointer; border: 2px solid transparent; transition: box-shadow 0.1s; }
        .element:hover { border-color: #f1c40f !important; z-index: 50; }
        .element.selected { border-color: #e74c3c !important; z-index: 100; box-shadow: 0 0 10px rgba(231, 76, 60, 0.8); }
        .element .label { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 12px; font-weight: bold; pointer-events: none; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white; white-space: nowrap; color: black; }
        
        /* Elements visual styles */
        .el-seat { background: rgba(46, 204, 113, 0.6); border-radius: 6px; border: 1px solid #27ae60; }
        .el-seat[data-seattype="cubicle"] { background: rgba(52, 152, 219, 0.6); border-color: #2980b9; border-radius: 2px; }
        .el-seat[data-seattype="disabled"] { background: rgba(155, 89, 182, 0.6); border-color: #8e44ad; }
        
        .el-motion { background: rgba(243, 156, 18, 0.6); border: 1px solid #e67e22; border-radius: 6px; }
        .el-door { background: rgba(231, 76, 60, 0.6); border: 1px solid #c0392b; }
        .el-window { background: rgba(135, 206, 235, 0.5); border: 1px solid #0097e6; }
        .el-pillar { background: rgba(52, 73, 94, 0.8); border: 1px solid #2c3e50; }
        .el-wall { background: repeating-linear-gradient(45deg, #bdc3c7, #bdc3c7 10px, #95a5a6 10px, #95a5a6 20px); border: 1px solid #7f8c8d; }
        
        #room-layer { position: absolute; border: 3px dashed #3498db; background: transparent; pointer-events: none; z-index: 1; display: none; }
        #selection-box { position: absolute; border: 1px solid #3498db; background: rgba(52, 152, 219, 0.2); pointer-events: none; z-index: 9999; display: none; }
        .guide-line { position: absolute; background: #e74c3c; z-index: 200; pointer-events: none; }
        
        #properties { width: 300px; background: white; padding: 20px; box-sizing: border-box; border-left: 1px solid #bdc3c7; z-index: 10; display: flex; flex-direction: column; overflow-y: auto; box-shadow: -2px 0 5px rgba(0,0,0,0.05); }
        .prop-group { margin-bottom: 15px; }
        .prop-group label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 13px; color: #333; }
        .prop-group input, .prop-group select { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        .prop-group input:focus, .prop-group select:focus { outline: none; border-color: #3498db; }
        
        .rot-btn { flex: 1; padding: 8px 0; background: #f8f9fa; border: 1px solid #ccc; cursor: pointer; border-radius: 4px; font-size: 12px; text-align: center; }
        .rot-btn:hover { background: #e2e6ea; }
        .rot-btn.active { background: #3498db; color: white; border-color: #2980b9; font-weight: bold;}

        #save-btn { background: #27ae60; color: white; border: none; padding: 15px; cursor: pointer; font-size: 16px; margin-top: auto; font-weight: bold; border-radius: 4px; transition: 0.2s; }
        #save-btn:hover { background: #2ecc71; }

        .hotkey-hint { font-size: 12px; color: #bdc3c7; margin-top: 15px; line-height: 1.6; }
    </style>
</head>
<body>

<div id="toolbar">
    <h2>도구 모음</h2>
    <button class="tool-btn active" data-tool="select">👆 선택 / 이동 (V)</button>
    <button class="tool-btn" data-tool="room">📏 열람실 영역 설정</button>
    <hr style="width: 100%; border-color: #455a64; margin: 10px 0;">
    <button class="tool-btn" data-tool="seat">🪑 좌석 추가 (S)</button>
    <button class="tool-btn" data-tool="motion">⚡ 모션데스크 (M)</button>
    <button class="tool-btn" data-tool="wall">🧱 못쓰는 벽/공간 (B)</button>
    <button class="tool-btn" data-tool="window">🪟 창문 추가 (W)</button>
    <button class="tool-btn" data-tool="door">🚪 문 추가 (E)</button>
    <button class="tool-btn" data-tool="pillar">⬛ 기둥 추가 (P)</button>
    
    <div style="flex-grow: 1;"></div>
    <div class="hotkey-hint">
        <b>[ 단축키 안내 ]</b><br>
        * 도구 선택: 괄호 안의 영문자<br>
        * 다중 선택: 바탕 드래그 또는 Shift+클릭<br>
        * 복사/붙여넣기: Ctrl+C / Ctrl+V<br>
        * 객체 삭제: Delete / Backspace<br>
        * 미세이동: 화살표 키<br>
        * 회전: R 키<br>
        * 자석 기능: (단일 선택 시) 자동 스냅
    </div>
</div>

<div id="workspace">
    <div id="canvas-container">
        <img id="bg-image" src="/layout.png" alt="Layout Image" draggable="false" onerror="alert('layout.png 이미지를 찾을 수 없습니다. 같은 폴더에 layout.png를 준비해주세요.')">
        <div id="room-layer"></div>
        <div id="selection-box"></div>
        <div id="elements-layer"></div>
        <div id="guides-layer"></div>
    </div>
</div>

<div id="properties">
    <h2 style="margin-top:0; font-size: 18px; border-bottom: 1px solid #eee; padding-bottom: 10px;">객체 속성</h2>
    
    <div style="display: flex; gap: 5px; margin-bottom: 15px;">
        <button id="ui-btn-copy" style="flex:1; padding:8px; background:#3498db; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">복사(C)</button>
        <button id="ui-btn-paste" style="flex:1; padding:8px; background:#f39c12; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">붙여넣기(V)</button>
        <button id="ui-btn-delete" style="flex:1; padding:8px; background:#e74c3c; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">삭제(Del)</button>
    </div>

    <div id="no-selection" style="color: #888; font-size: 14px; text-align: center; margin-top: 20px; white-space: pre-wrap;">선택된 객체가 없습니다.</div>
    <div id="prop-form" style="display: none;">
        <div class="prop-group">
            <label>종류</label>
            <input type="text" id="prop-category" disabled style="background:#f9f9f9;">
        </div>
        <div class="prop-group">
            <label>ID / 이름</label>
            <input type="text" id="prop-id" placeholder="예: S01">
        </div>
        <div class="prop-group" id="group-seat-type" style="display: none;">
            <label>좌석 종류</label>
            <select id="prop-seat-type">
                <option value="normal">일반 좌석</option>
                <option value="cubicle">칸막이 좌석</option>
                <option value="disabled">장애인석</option>
            </select>
        </div>
        <div style="display: flex; gap: 10px;">
            <div class="prop-group" style="flex: 1;">
                <label>X 좌표 (영역 기준)</label>
                <input type="number" id="prop-x">
            </div>
            <div class="prop-group" style="flex: 1;">
                <label>Y 좌표 (영역 기준)</label>
                <input type="number" id="prop-y">
            </div>
        </div>
        <div style="display: flex; gap: 10px;">
            <div class="prop-group" style="flex: 1;">
                <label>너비</label>
                <input type="number" id="prop-w">
            </div>
            <div class="prop-group" style="flex: 1;">
                <label>높이</label>
                <input type="number" id="prop-h">
            </div>
        </div>
        <div class="prop-group">
            <label>회전 방향</label>
            <div style="display: flex; gap: 5px;">
                <button class="rot-btn" data-deg="0">북(0°)</button>
                <button class="rot-btn" data-deg="90">동(90°)</button>
                <button class="rot-btn" data-deg="180">남(180°)</button>
                <button class="rot-btn" data-deg="270">서(270°)</button>
            </div>
        </div>
    </div>
    
    <button id="save-btn">저장하기</button>
</div>

<script>
    const state = {
        tool: 'select',
        elements: [],
        room: null,
        selectedIds: [],
        clipboard: []
    };
    
    const defaults = {
        seat: { w: 30, h: 30 },
        motion: { w: 40, h: 30 },
        window: { w: 100, h: 10 },
        door: { w: 40, h: 10 },
        pillar: { w: 20, h: 20 },
        wall: { w: 50, h: 50 }
    };

    const canvasContainer = document.getElementById('canvas-container');
    const elementsLayer = document.getElementById('elements-layer');
    const roomLayer = document.getElementById('room-layer');
    const guidesLayer = document.getElementById('guides-layer');
    
    const propForm = document.getElementById('prop-form');
    const noSelection = document.getElementById('no-selection');
    const pCat = document.getElementById('prop-category');
    const pId = document.getElementById('prop-id');
    const pTypeGroup = document.getElementById('group-seat-type');
    const pType = document.getElementById('prop-seat-type');
    const pX = document.getElementById('prop-x');
    const pY = document.getElementById('prop-y');
    const pW = document.getElementById('prop-w');
    const pH = document.getElementById('prop-h');

    fetch('/data')
        .then(res => res.json())
        .then(data => {
            if (data.room) {
                state.room = data.room;
                renderRoom();
            }
            if (data.elements) {
                state.elements = data.elements.map(el => {
                    return {
                        ...el,
                        _id: generateId(),
                        x: state.room ? el.x + state.room.x : el.x,
                        y: state.room ? el.y + state.room.y : el.y
                    };
                });
            } else {
                state.elements = [];
            }
            renderAll();
        })
        .catch(err => console.error("Error loading data:", err));

    function generateId() { return Math.random().toString(36).substr(2, 9); }

    function renderRoom() {
        if (state.room) {
            roomLayer.style.display = 'block';
            roomLayer.style.left = state.room.x + 'px';
            roomLayer.style.top = state.room.y + 'px';
            roomLayer.style.width = state.room.w + 'px';
            roomLayer.style.height = state.room.h + 'px';
        } else {
            roomLayer.style.display = 'none';
        }
    }

    document.getElementById('save-btn').addEventListener('click', () => {
        const rx = state.room ? state.room.x : 0;
        const ry = state.room ? state.room.y : 0;

        const elementsToSave = state.elements.map(el => {
            const obj = {
                category: el.category,
                x: el.x - rx,
                y: el.y - ry,
                w: el.w,
                h: el.h,
                r: el.r
            };
            if (el.id && el.id.trim() !== '') {
                obj.id = el.id.trim();
            } else {
                obj.id = "";
            }
            if (el.category === 'seat') {
                obj.type = el.type;
            }
            return obj;
        });

        const out = { 
            room: state.room,
            elements: elementsToSave,
            seat: elementsToSave.filter(e => e.category === 'seat'),
            motion: elementsToSave.filter(e => e.category === 'motion'),
            door: elementsToSave.filter(e => e.category === 'door'),
            window: elementsToSave.filter(e => e.category === 'window'),
            pillar: elementsToSave.filter(e => e.category === 'pillar'),
            wall: elementsToSave.filter(e => e.category === 'wall')
        };
        
        fetch('/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(out)
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                alert('저장되었습니다! (layout_data.json)\n모든 좌표는 열람실 영역 기준으로 저장되었습니다.');
            } else {
                alert('저장 실패: ' + data.message);
            }
        });
    });

    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.tool = btn.dataset.tool;
            if (state.tool !== 'select') {
                canvasContainer.style.cursor = 'crosshair';
                state.selectedIds = [];
                renderAll();
            } else {
                canvasContainer.style.cursor = 'default';
            }
        });
    });

    function renderAll() {
        elementsLayer.innerHTML = '';
        state.elements.forEach(el => {
            const div = document.createElement('div');
            div.className = `element el-${el.category} ${state.selectedIds.includes(el._id) ? 'selected' : ''}`;
            div.dataset.uid = el._id;
            div.style.left = `${el.x}px`;
            div.style.top = `${el.y}px`;
            div.style.width = `${el.w}px`;
            div.style.height = `${el.h}px`;
            div.style.transform = `rotate(${el.r || 0}deg)`;
            
            if (el.category === 'seat') {
                div.dataset.seattype = el.type || 'normal';
            }

            const label = document.createElement('div');
            label.className = 'label';
            label.innerText = el.id || '';
            div.appendChild(label);

            elementsLayer.appendChild(div);
        });
        updatePropertiesPanel();
    }

    let isDragging = false;
    let dragTarget = null;
    let startX, startY;
    
    let isDrawing = false;
    let drawStartX, drawStartY;

    let isSelecting = false;
    let selectStartX, selectStartY;

    canvasContainer.addEventListener('mousedown', (e) => {
        const rect = canvasContainer.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (state.tool === 'room' || state.tool === 'wall') {
            isDrawing = true;
            drawStartX = x;
            drawStartY = y;
            if (state.tool === 'room') {
                state.room = { x: x, y: y, w: 0, h: 0 };
                renderRoom();
            } else {
                const newEl = {
                    _id: generateId(),
                    category: 'wall',
                    id: '',
                    x: Math.round(x),
                    y: Math.round(y),
                    w: 0,
                    h: 0,
                    r: 0
                };
                state.elements.push(newEl);
                state.selectedIds = [newEl._id];
                renderAll();
            }
            return;
        }

        if (state.tool !== 'select') {
            const newEl = {
                _id: generateId(),
                category: state.tool,
                id: '',
                type: 'normal',
                x: Math.round(x - defaults[state.tool].w / 2),
                y: Math.round(y - defaults[state.tool].h / 2),
                w: defaults[state.tool].w,
                h: defaults[state.tool].h,
                r: 0
            };
            state.elements.push(newEl);
            state.selectedIds = [newEl._id];
            document.querySelector('[data-tool="select"]').click();
            return;
        }

        const elDiv = e.target.closest('.element');
        if (elDiv) {
            const uid = elDiv.dataset.uid;
            dragTarget = uid;
            if (!state.selectedIds.includes(uid)) {
                if (e.shiftKey) {
                    state.selectedIds.push(uid);
                } else {
                    state.selectedIds = [uid];
                }
            } else if (e.shiftKey) {
                state.selectedIds = state.selectedIds.filter(id => id !== uid);
                renderAll();
                return;
            }
            
            isDragging = true;
            state.selectedIds.forEach(id => {
                const el = state.elements.find(e => e._id === id);
                if(el) { el._initialX = el.x; el._initialY = el.y; }
            });
            startX = e.clientX;
            startY = e.clientY;
            renderAll();
            e.stopPropagation();
        } else {
            isSelecting = true;
            selectStartX = x;
            selectStartY = y;
            if (!e.shiftKey) {
                state.selectedIds = [];
                renderAll();
            }
        }
    });

    window.addEventListener('mousemove', (e) => {
        const rect = canvasContainer.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        if (isDrawing) {
            const curX = Math.min(drawStartX, mx);
            const curY = Math.min(drawStartY, my);
            const curW = Math.abs(mx - drawStartX);
            const curH = Math.abs(my - drawStartY);

            if (state.tool === 'room') {
                state.room.x = curX;
                state.room.y = curY;
                state.room.w = curW;
                state.room.h = curH;
                renderRoom();
            } else if (state.tool === 'wall') {
                const el = state.elements.find(el => el._id === state.selectedIds[0]);
                if (el) {
                    el.x = Math.round(curX);
                    el.y = Math.round(curY);
                    el.w = Math.round(curW);
                    el.h = Math.round(curH);
                    const elDiv = document.querySelector(`[data-uid="${el._id}"]`);
                    if (elDiv) {
                        elDiv.style.left = `${el.x}px`;
                        elDiv.style.top = `${el.y}px`;
                        elDiv.style.width = `${el.w}px`;
                        elDiv.style.height = `${el.h}px`;
                    }
                }
            }
            return;
        }

        if (isSelecting) {
            const curX = Math.min(selectStartX, mx);
            const curY = Math.min(selectStartY, my);
            const curW = Math.abs(mx - selectStartX);
            const curH = Math.abs(my - selectStartY);
            const selBox = document.getElementById('selection-box');
            selBox.style.display = 'block';
            selBox.style.left = curX + 'px';
            selBox.style.top = curY + 'px';
            selBox.style.width = curW + 'px';
            selBox.style.height = curH + 'px';
            return;
        }

        if (isDragging && state.selectedIds.length > 0) {
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            
            // dragTarget 기준으로 스냅 계산
            const targetEl = state.elements.find(e => e._id === dragTarget);
            if (!targetEl) return;
            
            let proposedX = Math.round(targetEl._initialX + dx);
            let proposedY = Math.round(targetEl._initialY + dy);
            
            const SNAP_DIST = 8;
            let guides = [];
            let snappedX = false;
            let snappedY = false;

            state.elements.forEach(other => {
                if(state.selectedIds.includes(other._id)) return;
                
                // X축 스냅
                if (!snappedX) {
                    if (Math.abs(proposedX - other.x) < SNAP_DIST) { proposedX = other.x; snappedX = true; guides.push({type:'v', pos: other.x}); }
                    else if (Math.abs(proposedX + targetEl.w - (other.x + other.w)) < SNAP_DIST) { proposedX = other.x + other.w - targetEl.w; snappedX = true; guides.push({type:'v', pos: other.x + other.w}); }
                    else if (Math.abs(proposedX - (other.x + other.w)) < SNAP_DIST) { proposedX = other.x + other.w; snappedX = true; guides.push({type:'v', pos: other.x + other.w}); }
                    else if (Math.abs(proposedX + targetEl.w - other.x) < SNAP_DIST) { proposedX = other.x - targetEl.w; snappedX = true; guides.push({type:'v', pos: other.x}); }
                }
                // Y축 스냅
                if (!snappedY) {
                    if (Math.abs(proposedY - other.y) < SNAP_DIST) { proposedY = other.y; snappedY = true; guides.push({type:'h', pos: other.y}); }
                    else if (Math.abs(proposedY + targetEl.h - (other.y + other.h)) < SNAP_DIST) { proposedY = other.y + other.h - targetEl.h; snappedY = true; guides.push({type:'h', pos: other.y + other.h}); }
                    else if (Math.abs(proposedY - (other.y + other.h)) < SNAP_DIST) { proposedY = other.y + other.h; snappedY = true; guides.push({type:'h', pos: other.y + other.h}); }
                    else if (Math.abs(proposedY + targetEl.h - other.y) < SNAP_DIST) { proposedY = other.y - targetEl.h; snappedY = true; guides.push({type:'h', pos: other.y}); }
                }
            });

            drawGuides(guides);

            // targetEl가 실제로 이동한 거리 (스냅 적용된 최종 거리)
            const finalDx = proposedX - targetEl._initialX;
            const finalDy = proposedY - targetEl._initialY;

            // 모든 선택된 요소에 동일한 이동거리 적용
            state.selectedIds.forEach(id => {
                const el = state.elements.find(e => e._id === id);
                if (el) {
                    el.x = el._initialX + finalDx;
                    el.y = el._initialY + finalDy;
                    const elDiv = document.querySelector(`[data-uid="${id}"]`);
                    if (elDiv) {
                        elDiv.style.left = `${el.x}px`;
                        elDiv.style.top = `${el.y}px`;
                    }
                }
            });

            if (state.selectedIds.length === 1) {
                updatePosInputs(targetEl.x, targetEl.y);
            }
        }
    });

    window.addEventListener('mouseup', (e) => {
        if (isDrawing) {
            isDrawing = false;
            if (state.tool === 'wall') {
                const el = state.elements.find(e => e._id === state.selectedIds[0]);
                if (el && el.w < 5 && el.h < 5) {
                    el.w = defaults.wall.w;
                    el.h = defaults.wall.h;
                    el.x = Math.round(el.x - el.w / 2);
                    el.y = Math.round(el.y - el.h / 2);
                    renderAll();
                }
            }
            document.querySelector('[data-tool="select"]').click();
            updatePropertiesPanel(); 
        }
        if (isSelecting) {
            isSelecting = false;
            const selBox = document.getElementById('selection-box');
            selBox.style.display = 'none';
            
            const rect = canvasContainer.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            
            const rx1 = Math.min(selectStartX, mx);
            const ry1 = Math.min(selectStartY, my);
            const rx2 = Math.max(selectStartX, mx);
            const ry2 = Math.max(selectStartY, my);
            
            state.elements.forEach(el => {
                const ex1 = el.x, ey1 = el.y;
                const ex2 = el.x + el.w, ey2 = el.y + el.h;
                if (!(rx2 < ex1 || rx1 > ex2 || ry2 < ey1 || ry1 > ey2)) {
                    if (!state.selectedIds.includes(el._id)) {
                        state.selectedIds.push(el._id);
                    }
                }
            });
            renderAll();
        }
        if (isDragging) {
            isDragging = false;
            dragTarget = null;
            guidesLayer.innerHTML = ''; 
            updatePropertiesPanel();
        }
    });

    function drawGuides(guides) {
        guidesLayer.innerHTML = '';
        guides.forEach(g => {
            const div = document.createElement('div');
            div.className = 'guide-line';
            if(g.type === 'v') {
                div.style.left = g.pos + 'px';
                div.style.top = '0px';
                div.style.width = '1px';
                div.style.height = '2000px';
            } else {
                div.style.top = g.pos + 'px';
                div.style.left = '0px';
                div.style.height = '1px';
                div.style.width = '2000px';
            }
            guidesLayer.appendChild(div);
        });
    }

    function updatePosInputs(absX, absY) {
        const rx = state.room ? state.room.x : 0;
        const ry = state.room ? state.room.y : 0;
        pX.value = absX - rx;
        pY.value = absY - ry;
    }

    function updatePropertiesPanel() {
        if (state.selectedIds.length === 0) {
            noSelection.style.display = 'block';
            noSelection.innerText = "선택된 객체가 없습니다.";
            propForm.style.display = 'none';
            return;
        }
        
        if (state.selectedIds.length > 1) {
            noSelection.style.display = 'block';
            noSelection.innerText = `${state.selectedIds.length}개의 객체가 선택되었습니다.\n\n다중 선택 상태에서는\n일괄 이동, 복사, 삭제만 가능합니다.`;
            propForm.style.display = 'none';
            return;
        }

        const el = state.elements.find(e => e._id === state.selectedIds[0]);
        if (!el) return;

        noSelection.style.display = 'none';
        propForm.style.display = 'block';

        pCat.value = el.category === 'motion' ? '모션데스크' :
                     el.category === 'seat' ? '좌석' :
                     el.category === 'wall' ? '못쓰는 벽/공간' : el.category;
                     
        pId.value = el.id || '';
        updatePosInputs(el.x, el.y);
        pW.value = el.w;
        pH.value = el.h;
        
        document.querySelectorAll('.rot-btn').forEach(btn => {
            btn.classList.remove('active');
            if (parseInt(btn.dataset.deg) === (el.r || 0)) {
                btn.classList.add('active');
            }
        });

        if (el.category === 'seat') {
            pTypeGroup.style.display = 'block';
            pType.value = el.type || 'normal';
        } else {
            pTypeGroup.style.display = 'none';
        }
    }

    document.querySelectorAll('.rot-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (state.selectedIds.length !== 1) return;
            const el = state.elements.find(x => x._id === state.selectedIds[0]);
            if (el) {
                el.r = parseInt(e.target.dataset.deg);
                renderAll();
            }
        });
    });

    const bindProp = (input, key, isNumber=false) => {
        input.addEventListener('input', (e) => {
            if (state.selectedIds.length !== 1) return;
            const el = state.elements.find(x => x._id === state.selectedIds[0]);
            if (el) {
                let val = isNumber ? (parseFloat(e.target.value) || 0) : e.target.value;
                if (key === 'x') {
                    const rx = state.room ? state.room.x : 0;
                    el.x = val + rx;
                } else if (key === 'y') {
                    const ry = state.room ? state.room.y : 0;
                    el.y = val + ry;
                } else {
                    el[key] = val;
                }
                renderAll();
            }
        });
    };

    bindProp(pId, 'id');
    bindProp(pType, 'type');
    bindProp(pX, 'x', true);
    bindProp(pY, 'y', true);
    bindProp(pW, 'w', true);
    bindProp(pH, 'h', true);

    function copySelected() {
        if (state.selectedIds.length === 0) return;
        state.clipboard = state.elements
            .filter(el => state.selectedIds.includes(el._id))
            .map(el => JSON.parse(JSON.stringify(el)));
            
        // 기존 ID의 숫자 순서대로 정렬하여, 붙여넣을 때 원래 순서가 유지되도록 함
        state.clipboard.sort((a, b) => {
            if (!a.id && !b.id) return 0;
            if (!a.id) return 1;
            if (!b.id) return -1;
            const matchA = a.id.match(/^(.*?)(\d+)$/);
            const matchB = b.id.match(/^(.*?)(\d+)$/);
            if (matchA && matchB && matchA[1] === matchB[1]) {
                return parseInt(matchA[2]) - parseInt(matchB[2]);
            }
            return a.id.localeCompare(b.id);
        });
            
        alert(`${state.clipboard.length}개의 객체가 복사되었습니다.\n붙여넣기 버튼이나 Ctrl+V를 누르세요.`);
    }

    function pasteClipboard() {
        if (state.clipboard.length === 0) {
            alert('먼저 객체를 복사해주세요.');
            return;
        }
        state.selectedIds = [];
        
        state.clipboard.forEach(clipEl => {
            const newEl = JSON.parse(JSON.stringify(clipEl));
            newEl._id = generateId();
            newEl.x += 30; // 약간 띄워서 복사
            newEl.y += 30;
            
            if (newEl.id && newEl.id.trim() !== '') {
                const match = newEl.id.match(/^(.*?)(\d+)$/);
                if (match) {
                    const prefix = match[1];
                    let maxNum = 0;
                    state.elements.forEach(el => {
                        if (el.id) {
                            const elMatch = el.id.match(/^(.*?)(\d+)$/);
                            if (elMatch && elMatch[1] === prefix) {
                                const n = parseInt(elMatch[2]);
                                if (n > maxNum) maxNum = n;
                            }
                        }
                    });
                    newEl.id = prefix + (maxNum + 1);
                }
            }
            
            state.elements.push(newEl);
            state.selectedIds.push(newEl._id);
        });
        
        state.clipboard.forEach(c => { c.x += 30; c.y += 30; }); 
        renderAll();
    }

    document.getElementById('ui-btn-copy').addEventListener('click', copySelected);
    document.getElementById('ui-btn-paste').addEventListener('click', pasteClipboard);
    document.getElementById('ui-btn-delete').addEventListener('click', deleteSelected);

    function deleteSelected() {
        if (state.selectedIds.length === 0) return;
        state.elements = state.elements.filter(e => !state.selectedIds.includes(e._id));
        state.selectedIds = [];
        renderAll();
    }

    window.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return; 
        
        const keyMap = {
            'v': 'select', 's': 'seat', 'm': 'motion', 'b': 'wall', 'w': 'window', 'e': 'door', 'p': 'pillar'
        };
        
        let toolKey = e.key.toLowerCase();
        if (e.code === 'KeyV') toolKey = 'v';
        if (e.code === 'KeyS') toolKey = 's';
        if (e.code === 'KeyM') toolKey = 'm';
        if (e.code === 'KeyB') toolKey = 'b';
        if (e.code === 'KeyW') toolKey = 'w';
        if (e.code === 'KeyE') toolKey = 'e';
        if (e.code === 'KeyP') toolKey = 'p';

        if (keyMap[toolKey]) {
            const btn = document.querySelector(`[data-tool="${keyMap[toolKey]}"]`);
            if (btn) btn.click();
            return;
        }

        if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'v' || e.code === 'KeyV')) {
            pasteClipboard();
            e.preventDefault();
            return;
        }

        if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'c' || e.code === 'KeyC')) {
            copySelected();
            e.preventDefault();
            return;
        }

        if (state.selectedIds.length === 0) return;

        const moveStep = e.shiftKey ? 10 : 1;

        if (e.key === 'ArrowUp') { state.selectedIds.forEach(id=>{let el=state.elements.find(x=>x._id===id); if(el) el.y -= moveStep;}); e.preventDefault(); renderAll(); return; }
        if (e.key === 'ArrowDown') { state.selectedIds.forEach(id=>{let el=state.elements.find(x=>x._id===id); if(el) el.y += moveStep;}); e.preventDefault(); renderAll(); return; }
        if (e.key === 'ArrowLeft') { state.selectedIds.forEach(id=>{let el=state.elements.find(x=>x._id===id); if(el) el.x -= moveStep;}); e.preventDefault(); renderAll(); return; }
        if (e.key === 'ArrowRight') { state.selectedIds.forEach(id=>{let el=state.elements.find(x=>x._id===id); if(el) el.x += moveStep;}); e.preventDefault(); renderAll(); return; }
        
        if (e.key === 'Delete' || e.key === 'Backspace') {
            deleteSelected();
            return;
        }

        if (e.key.toLowerCase() === 'r' || e.code === 'KeyR') {
            state.selectedIds.forEach(id=>{
                let el = state.elements.find(x=>x._id===id);
                if(el) el.r = ((el.r || 0) + 90) % 360;
            });
            renderAll();
            return;
        }
    });

</script>
</body>
</html>
"""

class EditorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/' or self.path == '/editor.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
            return
        elif self.path == '/data':
            json_path = os.path.join(DIRECTORY, 'layout_data.json')
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        self.wfile.write(f.read().encode('utf-8'))
                except Exception:
                    self.wfile.write(json.dumps({"elements": []}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"elements": []}).encode('utf-8'))
            return
        
        return super().do_GET()

    def do_POST(self):
        if self.path == '/save':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                json_path = os.path.join(DIRECTORY, 'layout_data.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def find_free_port(start_port=8000):
    port = start_port
    while port < 8100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                port += 1
    return 0

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    port = find_free_port(8000)
    
    try:
        with socketserver.TCPServer(("", port), EditorHandler) as httpd:
            print(f"==================================================")
            print(f"🎨 열람실 배치도 에디터가 실행되었습니다!")
            print(f"👉 브라우저 주소창에 아래 링크를 입력하세요:")
            print(f"http://localhost:{port}")
            print(f"==================================================")
            print("종료하려면 이 창에서 Ctrl+C를 누르세요.")
            
            url = f"http://localhost:{port}"
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
            
            httpd.serve_forever()
    except OSError as e:
        print(f"서버를 실행할 수 없습니다: {e}")

if __name__ == "__main__":
    run_server()