import flet as ft
import time
import threading
import json
from flet_audio import Audio

async def main(page: ft.Page):
    page.title = "极简健身计时器"
    page.theme_mode = ft.ThemeMode.DARK # 酷炫暗黑模式
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    # --- 1. 核心状态变量 ---
    def _debug(msg: str):
        print(f"[DEBUG] {msg}", flush=True)

    workout_plan = []  # 存放解析后的任务列表
    current_task_idx = 0
    rest_cancel_event = threading.Event()
    rest_pause_event = threading.Event()
    rest_pause_event.set()  # not paused
    is_resting = False

    work_cancel_event = threading.Event()
    work_pause_event = threading.Event()
    work_pause_event.set()
    is_working = False
    
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

    # 显示当前状态的大字
    lbl_status = ft.Text("准备开始", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
    lbl_detail = ft.Text("点击下方解析计划", size=20)
    
    # 倒计时显示（休息）
    lbl_timer = ft.Text("00:00", size=60, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
    lbl_timer.visible = False
    # 动作计时（例如：平板支撑 60秒）
    lbl_work_timer = ft.Text("00:00", size=48, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
    lbl_work_timer.visible = False

    # 按钮
    btn_action = ft.Button(content="解析并开始训练", width=200, height=50)
    btn_pause = ft.Button(content="暂停", width=100, height=40, visible=False, disabled=True)
    btn_stop = ft.Button(content="终止", width=100, height=40, visible=False, disabled=True)
    btn_work_pause = ft.Button(content="暂停", width=100, height=40, visible=False, disabled=True)
    btn_work_stop = ft.Button(content="结束本组", width=110, height=40, visible=False, disabled=True)

    dd_plans = ft.Dropdown(label="选择计划", width=260, options=[])
    btn_save_plan = ft.Button(content="保存为新计划", width=120, height=40)
    btn_update_plan = ft.Button(content="保存修改", width=100, height=40)
    btn_delete_plan = ft.Button(content="删除计划", width=100, height=40)

    def _refresh_plan_dropdown(selected_id: str | None = None):
        _debug(f"_refresh_plan_dropdown(selected_id={selected_id}, total={len(plans)})")
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
        _debug(f"_apply_plan(plan_id={plan_id})")
        if plan_id not in plans:
            _debug(f"_apply_plan skipped: missing plan_id={plan_id}")
            return
        txt_input.value = plans[plan_id].get("text", "") or ""
        await _set_last_plan_id(plan_id)
        last_plan_id = plan_id
        page.update()

    async def on_plan_change(e):
        _debug(f"on_plan_change triggered, dd_plans.value={dd_plans.value}")
        if dd_plans.value:
            await _apply_plan(dd_plans.value)
            if auto_back_home_after_plan_select:
                _set_tab("home")

    dd_plans.on_change = on_plan_change

    async def on_save_plan(e):
        nonlocal plans, last_plan_id
        _debug("on_save_plan triggered")
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
        _debug(f"on_save_plan done, new plan_id={plan_id}")

    btn_save_plan.on_click = on_save_plan

    async def on_update_plan(e):
        nonlocal plans, last_plan_id
        _debug("on_update_plan triggered")
        pid = dd_plans.value or last_plan_id
        if not pid:
            _debug("on_update_plan skipped: no pid")
            return
        if pid not in plans:
            _debug(f"on_update_plan skipped: missing pid={pid}")
            return
        text = txt_input.value or ""
        plans[pid]["name"] = _infer_plan_name(text)
        plans[pid]["text"] = text
        await _save_plans(plans)
        await _set_last_plan_id(pid)
        last_plan_id = pid
        _refresh_plan_dropdown(pid)
        _debug(f"on_update_plan done, pid={pid}")

    btn_update_plan.on_click = on_update_plan

    async def _delete_plan_confirmed():
        nonlocal plans, last_plan_id
        _debug("_delete_plan_confirmed triggered")
        pid = dd_plans.value or last_plan_id
        if not pid or pid not in plans:
            _debug(f"_delete_plan_confirmed skipped, pid={pid}")
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
        _debug(f"_delete_plan_confirmed done, next_id={next_id}")

    async def on_delete_plan(e):
        _debug("on_delete_plan triggered -> show confirm dialog")
        confirm_dialog.title = ft.Text("确认删除")
        confirm_dialog.content = ft.Text("确定要删除当前计划吗？此操作不可撤销。")
        confirm_dialog.open = True
        page.update()

    btn_delete_plan.on_click = on_delete_plan

    _refresh_plan_dropdown(last_plan_id)

    async def on_confirm_delete(e):
        _debug("on_confirm_delete triggered")
        confirm_dialog.open = False
        page.update()
        await _delete_plan_confirmed()

    def on_cancel_delete(e):
        _debug("on_cancel_delete triggered")
        confirm_dialog.open = False
        page.update()

    confirm_dialog = ft.AlertDialog(
        modal=True,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("取消", on_click=on_cancel_delete),
            ft.TextButton("删除", on_click=on_confirm_delete),
        ],
    )
    page.dialog = confirm_dialog

    auto_back_home_after_plan_select = True
    current_tab = "home"
    btn_nav_home = ft.Button(content="首页", width=96, height=44, disabled=True)
    btn_nav_plan = ft.Button(content="计划", width=96, height=44)

    # --- 3. 逻辑函数 ---
    def parse_plan(text):
        """解析极简文本，生成任务列表"""
        plan = []
        lines = text.strip().split('\n')

        def _extract_int(raw: str, default: int = 0) -> int:
            digits = ''.join(ch for ch in (raw or "") if ch.isdigit())
            return int(digits) if digits else default

        def _parse_duration_seconds(raw: str) -> int:
            t = (raw or "").strip().lower().replace(" ", "")
            if not t:
                return 0
            if t in {"无", "none", "n/a", "na", "-"}:
                return 0
            if "无" in t and not any(ch.isdigit() for ch in t):
                return 0

            # 形如 1分钟30秒 / 2分 / 45秒 / 15s
            if "分" in t:
                min_part, sec_part = t.split("分", 1)
                mins = _extract_int(min_part, 0)
                secs = _extract_int(sec_part, 0) if ("秒" in sec_part or sec_part.endswith("s")) else 0
                return mins * 60 + secs

            if "秒" in t or t.endswith("s"):
                return _extract_int(t, 0)

            # 纯数字时按秒处理（主要用于休息字段）
            return _extract_int(t, 0)

        for line in lines:
            if not line or '|' not in line: continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                # 提取组数和休息秒数
                sets = _extract_int(parts[1], 0)
                if sets <= 0:
                    continue
                rest_sec = _parse_duration_seconds(parts[3])
                target_raw = parts[2]

                def _parse_target(t: str):
                    tl = (t or "").strip().lower().replace(" ", "")
                    if "秒" in tl or "分" in tl or tl.endswith("s"):
                        return {"kind": "time", "seconds": _parse_duration_seconds(t)}
                    return {"kind": "reps", "text": target_raw}
                
                # 拆分成具体的每一组任务
                for s in range(sets):
                    target = _parse_target(target_raw)
                    plan.append({
                        "name": parts[0],
                        "set_info": f"第 {s+1} 组 / 共 {sets} 组",
                        "target": target,
                        "rest": rest_sec,
                    })
        return plan

    def run_work_timer(seconds, rest_seconds_after):
        """动作计时（例如平板支撑 60秒），结束后自动进入休息"""
        nonlocal is_working
        is_working = True
        work_cancel_event.clear()
        work_pause_event.set()

        lbl_work_timer.visible = True
        btn_action.disabled = True
        btn_work_pause.visible = True
        btn_work_stop.visible = True
        btn_work_pause.disabled = False
        btn_work_stop.disabled = False
        btn_work_pause.content = "暂停"
        page.update()

        remaining = int(seconds)
        while remaining >= 0:
            if work_cancel_event.is_set():
                break
            work_pause_event.wait()
            mins, secs = divmod(remaining, 60)
            lbl_work_timer.value = f"{mins:02d}:{secs:02d}"
            page.update()
            time.sleep(1)
            remaining -= 1

        canceled = work_cancel_event.is_set()
        if not canceled:
            if getattr(page, "haptic_feedback", None):
                page.haptic_feedback.heavy_impact()
            if audio_player:
                audio_player.play()

        lbl_work_timer.visible = False
        btn_work_pause.visible = False
        btn_work_stop.visible = False
        btn_work_pause.disabled = True
        btn_work_stop.disabled = True
        btn_action.disabled = False
        is_working = False
        page.update()

        if canceled:
            return

        # 自动进入休息
        lbl_status.value = "休息中..."
        lbl_detail.value = "深呼吸，准备下一组"
        btn_action.content = "倒计时中..."
        page.update()
        threading.Thread(target=run_rest_timer, args=(int(rest_seconds_after),), daemon=True).start()

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
            tgt = task["target"]
            if isinstance(tgt, dict) and tgt.get("kind") == "time":
                lbl_detail.value = f"{task['set_info']}  目标: {int(tgt.get('seconds', 0))} 秒"
            else:
                lbl_detail.value = f"{task['set_info']}  目标: {tgt.get('text') if isinstance(tgt, dict) else tgt}"
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

            tgt = task.get("target")
            if isinstance(tgt, dict) and tgt.get("kind") == "time" and int(tgt.get("seconds", 0)) > 0:
                lbl_status.value = "动作计时中..."
                lbl_detail.value = "保持节奏"
                btn_action.content = "计时中..."
                page.update()
                threading.Thread(
                    target=run_work_timer,
                    args=(int(tgt["seconds"]), int(task["rest"])),
                    daemon=True,
                ).start()
            else:
                lbl_status.value = "休息中..."
                lbl_detail.value = "深呼吸，准备下一组"
                btn_action.content = "倒计时中..."
                page.update()
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

    def on_work_pause_click(e):
        if not is_working:
            return
        if work_pause_event.is_set():
            work_pause_event.clear()
            btn_work_pause.content = "继续"
        else:
            work_pause_event.set()
            btn_work_pause.content = "暂停"
        page.update()

    def on_work_stop_click(e):
        nonlocal is_working
        if not is_working:
            return
        work_cancel_event.set()
        work_pause_event.set()
        lbl_work_timer.visible = False
        btn_work_pause.visible = False
        btn_work_stop.visible = False
        btn_action.disabled = False
        is_working = False
        btn_action.content = "完成本组，开始休息"
        page.update()

    btn_work_pause.on_click = on_work_pause_click
    btn_work_stop.on_click = on_work_stop_click

    def _set_tab(tab: str):
        nonlocal current_tab
        current_tab = tab
        is_home = tab == "home"
        _debug(f"_set_tab -> {tab}")
        home_view.visible = is_home
        plan_view.visible = not is_home
        btn_nav_home.disabled = is_home
        btn_nav_plan.disabled = not is_home
        page.update()

    def on_nav_home(e):
        _set_tab("home")

    def on_nav_plan(e):
        _set_tab("plan")

    btn_nav_home.on_click = on_nav_home
    btn_nav_plan.on_click = on_nav_plan

    home_view = ft.Container(
        expand=True,
        visible=True,
        content=ft.Column(
            controls=[
                ft.Text("自律即自由", size=20, color=ft.Colors.GREY_500),
                txt_input,
                ft.Divider(),
                lbl_status,
                lbl_detail,
                lbl_timer,
                lbl_work_timer,
                ft.Container(height=30), # 占位空隙
                ft.Row([btn_pause, btn_stop], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                ft.Row([btn_work_pause, btn_work_stop], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                btn_action,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    cb_auto_back = ft.Checkbox(label="选择历史计划后自动返回首页", value=auto_back_home_after_plan_select)

    def on_auto_back_toggle(e):
        nonlocal auto_back_home_after_plan_select
        auto_back_home_after_plan_select = bool(cb_auto_back.value)
        _debug(f"auto_back_home_after_plan_select={auto_back_home_after_plan_select}")

    cb_auto_back.on_change = on_auto_back_toggle

    plan_view = ft.Container(
        expand=True,
        visible=False,
        content=ft.Column(
            controls=[
                ft.Text("计划管理", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("在这里选择历史计划，或保存/修改/删除计划。", color=ft.Colors.GREY_400),
                cb_auto_back,
                dd_plans,
                ft.Row([btn_save_plan, btn_update_plan, btn_delete_plan], spacing=10),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
    )

    # --- 4. 组装页面 ---
    page.add(
        ft.Row(
            controls=[
                ft.Container(
                    width=110,
                    padding=ft.padding.only(top=8),
                    content=ft.Column(
                        controls=[
                            ft.Text("导航", size=16, weight=ft.FontWeight.BOLD),
                            btn_nav_home,
                            btn_nav_plan,
                        ],
                        spacing=8,
                    ),
                ),
                ft.VerticalDivider(width=1),
                ft.Container(
                    expand=True,
                    padding=16,
                    content=ft.Stack([home_view, plan_view], expand=True),
                ),
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )

# 运行APP
ft.run(main)
