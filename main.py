import flet as ft
import time
import threading
import json
from flet_audio import Audio

async def main(page: ft.Page):
    page.title = "极简健身计时器"
    page.theme_mode = ft.ThemeMode.DARK # 酷炫暗黑模式
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --- 1. 核心状态变量 ---
    workout_plan = []  # 存放解析后的任务列表
    current_task_idx = 0
    rest_cancel_event = threading.Event()
    rest_pause_event = threading.Event()
    rest_pause_event.set()  # not paused
    is_resting = False
    
    # 提示音：使用 flet-audio 插件（支持移动端）
    audio_player = Audio(src="assets/ding.wav", autoplay=False)
    page.overlay.append(audio_player)

    # --- 2. UI 控件 ---
    # 计划存储（本地持久化到客户端）
    STORAGE_KEY = "plans_v1"
    LAST_PLAN_ID_KEY = "last_plan_id_v1"
    prefs = ft.SharedPreferences()

    async def _prefs_get(key: str, default=None):
        try:
            return await prefs.get(key)
        except Exception:
            return default

    async def _prefs_set(key: str, value):
        try:
            await prefs.set(key, value)
        except Exception:
            pass

    async def _load_plans():
        raw = await _prefs_get(STORAGE_KEY)
        if not raw:
            return {}
        try:
            plans = json.loads(raw)
            return plans if isinstance(plans, dict) else {}
        except Exception:
            return {}

    async def _save_plans(plans: dict):
        await _prefs_set(STORAGE_KEY, json.dumps(plans, ensure_ascii=False))

    async def _get_last_plan_id():
        return await _prefs_get(LAST_PLAN_ID_KEY)

    async def _set_last_plan_id(plan_id: str):
        await _prefs_set(LAST_PLAN_ID_KEY, plan_id)

    def _default_plan_text():
        return "俯卧撑 | 4组 | 力竭 | 休90\n下斜俯卧撑 | 3组 | 15次 | 休60"

    def _infer_plan_name(text: str):
        first_line = (text or "").strip().splitlines()[0].strip() if (text or "").strip() else "训练计划"
        return first_line.split("|")[0].strip() or "训练计划"

    # SharedPreferences service might be unavailable in some runtimes;
    # fall back to in-memory storage to keep app usable.
    plans = await _load_plans()
    last_plan_id = await _get_last_plan_id()
    initial_text = ""
    if last_plan_id and last_plan_id in plans:
        initial_text = plans[last_plan_id].get("text", "") or ""
    elif plans:
        # pick any existing plan deterministically
        first_id = sorted(plans.keys())[0]
        initial_text = plans[first_id].get("text", "") or ""
        await _set_last_plan_id(first_id)
        last_plan_id = first_id
    else:
        # seed a default plan for first run
        plan_id = "default"
        plans[plan_id] = {"name": "示例计划", "text": _default_plan_text()}
        await _save_plans(plans)
        await _set_last_plan_id(plan_id)
        last_plan_id = plan_id
        initial_text = plans[plan_id]["text"]

    # 输入框（用户手写或粘贴计划）
    txt_input = ft.TextField(
        multiline=True,
        min_lines=5,
        hint_text="输入格式例如:\n俯卧撑 | 4组 | 力竭 | 休90\n深蹲 | 3组 | 15次 | 休60",
        value=initial_text
    )

    async def _persist_current_text_as_last():
        nonlocal plans, last_plan_id
        text = txt_input.value or ""
        plan_id = last_plan_id or "default"
        name = plans.get(plan_id, {}).get("name") or _infer_plan_name(text)
        plans[plan_id] = {"name": name, "text": text}
        await _save_plans(plans)
        await _set_last_plan_id(plan_id)
        last_plan_id = plan_id

    async def on_input_change(e):
        # lightweight auto-save to "last used plan"
        await _persist_current_text_as_last()

    txt_input.on_change = on_input_change
    
    # 显示当前状态的大字
    lbl_status = ft.Text("准备开始", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
    lbl_detail = ft.Text("点击下方解析计划", size=20)
    
    # 倒计时显示
    lbl_timer = ft.Text("00:00", size=60, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
    lbl_timer.visible = False

    # 按钮
    btn_action = ft.Button(content="解析并开始训练", width=200, height=50)
    btn_pause = ft.Button(content="暂停", width=100, height=40, visible=False, disabled=True)
    btn_stop = ft.Button(content="终止", width=100, height=40, visible=False, disabled=True)

    dd_plans = ft.Dropdown(label="选择计划", width=260, options=[])
    btn_save_plan = ft.Button(content="保存为新计划", width=120, height=40)
    btn_delete_plan = ft.Button(content="删除计划", width=100, height=40)

    def _refresh_plan_dropdown(selected_id: str | None = None):
        dd_plans.options = [
            ft.dropdown.Option(key=pid, text=plans[pid].get("name") or pid)
            for pid in sorted(plans.keys())
        ]
        if selected_id and selected_id in plans:
            dd_plans.value = selected_id
        elif last_plan_id and last_plan_id in plans:
            dd_plans.value = last_plan_id
        elif plans:
            dd_plans.value = sorted(plans.keys())[0]
        page.update()

    async def _apply_plan(plan_id: str):
        nonlocal last_plan_id
        if plan_id not in plans:
            return
        txt_input.value = plans[plan_id].get("text", "") or ""
        await _set_last_plan_id(plan_id)
        last_plan_id = plan_id
        page.update()

    async def on_plan_change(e):
        if dd_plans.value:
            await _apply_plan(dd_plans.value)

    dd_plans.on_change = on_plan_change

    async def on_save_plan(e):
        nonlocal plans, last_plan_id
        text = txt_input.value or ""
        name = _infer_plan_name(text)
        # generate a simple unique id
        suffix = 1
        base_id = "plan"
        plan_id = f"{base_id}{suffix}"
        while plan_id in plans:
            suffix += 1
            plan_id = f"{base_id}{suffix}"
        plans[plan_id] = {"name": name, "text": text}
        await _save_plans(plans)
        await _set_last_plan_id(plan_id)
        last_plan_id = plan_id
        _refresh_plan_dropdown(plan_id)

    btn_save_plan.on_click = on_save_plan

    async def on_delete_plan(e):
        nonlocal plans, last_plan_id
        pid = dd_plans.value or last_plan_id
        if not pid or pid not in plans:
            return
        del plans[pid]
        if not plans:
            # keep at least one plan
            plans["default"] = {"name": "示例计划", "text": _default_plan_text()}
        await _save_plans(plans)
        # choose next selection
        next_id = sorted(plans.keys())[0]
        await _set_last_plan_id(next_id)
        last_plan_id = next_id
        _refresh_plan_dropdown(next_id)
        await _apply_plan(next_id)

    btn_delete_plan.on_click = on_delete_plan

    _refresh_plan_dropdown(last_plan_id)

    drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(height=10),
            ft.Text("训练计划", size=18, weight=ft.FontWeight.BOLD),
            dd_plans,
            ft.Row([btn_save_plan, btn_delete_plan], spacing=10),
        ]
    )
    page.drawer = drawer
    btn_open_drawer = ft.IconButton(icon=ft.Icons.MENU, tooltip="计划")

    def on_open_drawer(e):
        page.drawer.open = True
        page.update()

    btn_open_drawer.on_click = on_open_drawer

    # --- 3. 逻辑函数 ---
    def parse_plan(text):
        """解析极简文本，生成任务列表"""
        plan = []
        lines = text.strip().split('\n')
        for line in lines:
            if not line or '|' not in line: continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                # 提取组数和休息秒数 (利用简单的字符串截取，把"4组"变成 4)
                sets = int(''.join(filter(str.isdigit, parts[1])))
                rest_sec = int(''.join(filter(str.isdigit, parts[3])))
                
                # 拆分成具体的每一组任务
                for s in range(sets):
                    plan.append({
                        "name": parts[0],
                        "set_info": f"第 {s+1} 组 / 共 {sets} 组",
                        "target": parts[2],
                        "rest": rest_sec
                    })
        return plan

    def run_rest_timer(seconds):
        """后台倒计时线程"""
        nonlocal is_resting
        is_resting = True
        rest_cancel_event.clear()
        rest_pause_event.set()
        lbl_timer.visible = True
        btn_action.disabled = True # 休息期间禁用按钮防误触
        btn_pause.visible = True
        btn_stop.visible = True
        btn_pause.disabled = False
        btn_stop.disabled = False
        btn_pause.content = "暂停"
        page.update()
        
        remaining = seconds
        while remaining >= 0:
            if rest_cancel_event.is_set():
                break
            rest_pause_event.wait()
            i = remaining
            mins, secs = divmod(i, 60)
            lbl_timer.value = f"{mins:02d}:{secs:02d}"
            page.update()
            time.sleep(1)
            remaining -= 1
            
        canceled = rest_cancel_event.is_set()
        if not canceled:
            # 倒计时结束！震动 (+ 提示音如果可用)
            if getattr(page, "haptic_feedback", None):
                page.haptic_feedback.heavy_impact()  # 触发手机震动（移动端）
            if audio_player:
                audio_player.play()
        
        # 准备进入下一个动作
        lbl_timer.visible = False
        btn_action.disabled = False
        btn_pause.disabled = True
        btn_stop.disabled = True
        btn_pause.visible = False
        btn_stop.visible = False
        btn_action.content = "完成本组，开始休息" if not canceled else "重新开始"
        is_resting = False
        update_ui_for_current_task()
        page.update()

    def update_ui_for_current_task():
        nonlocal current_task_idx
        if current_task_idx < len(workout_plan):
            task = workout_plan[current_task_idx]
            lbl_status.value = task["name"]
            lbl_detail.value = f"{task['set_info']}  目标: {task['target']}"
        else:
            lbl_status.value = "🎉 训练全部完成！"
            lbl_detail.value = "去喝点蛋白粉吧！"
            btn_action.content = "重新开始"

    def on_btn_click(e):
        nonlocal current_task_idx, workout_plan
        
        # 阶段一：首次点击，解析文本
        if btn_action.content == "解析并开始训练" or btn_action.content == "重新开始":
            workout_plan = parse_plan(txt_input.value)
            if not workout_plan:
                lbl_detail.value = "文本格式错误，请检查！"
                page.update()
                return
            
            current_task_idx = 0
            txt_input.visible = False # 隐藏输入框，进入专注模式
            btn_action.content = "完成本组，开始休息"
            update_ui_for_current_task()
            page.update()
            
        # 阶段二：训练中点击，触发休息倒计时
        elif btn_action.content == "完成本组，开始休息":
            task = workout_plan[current_task_idx]
            current_task_idx += 1
            
            lbl_status.value = "休息中..."
            lbl_detail.value = "深呼吸，准备下一组"
            btn_action.content = "倒计时中..."
            
            # 开启新线程跑倒计时，防止UI卡死
            threading.Thread(target=run_rest_timer, args=(task["rest"],), daemon=True).start()

    # 绑定按钮事件
    btn_action.on_click = on_btn_click

    def on_pause_click(e):
        # toggle pause/resume
        if not is_resting:
            return
        if rest_pause_event.is_set():
            rest_pause_event.clear()
            btn_pause.content = "继续"
        else:
            rest_pause_event.set()
            btn_pause.content = "暂停"
        page.update()

    def on_stop_click(e):
        nonlocal workout_plan, current_task_idx, is_resting
        if not is_resting:
            return
        rest_cancel_event.set()
        rest_pause_event.set()
        workout_plan = []
        current_task_idx = 0
        txt_input.visible = True
        lbl_status.value = "已终止"
        lbl_detail.value = "你可以修改计划并重新开始"
        btn_action.content = "重新开始"
        page.update()

    btn_pause.on_click = on_pause_click
    btn_stop.on_click = on_stop_click

    # --- 4. 组装页面 ---
    page.add(
        ft.Row(
            [
                btn_open_drawer,
                ft.Text("自律即自由", size=20, color=ft.Colors.GREY_500),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        txt_input,
        ft.Divider(),
        lbl_status,
        lbl_detail,
        lbl_timer,
        ft.Container(height=30), # 占位空隙
        ft.Row([btn_pause, btn_stop], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        btn_action
    )

# 运行APP
ft.run(main)
