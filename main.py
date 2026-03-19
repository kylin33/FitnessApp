import flet as ft
from plan_meta import infer_plan_name
from plan_parser import parse_plan as parse_plan_text
from plan_store import (
    default_plan_text,
    init_plans_state,
    save_plans,
    set_last_plan_id,
)
from timer_engine import countdown
from ui_views import build_home_view, build_plan_view, build_sidebar

async def main(page: ft.Page):
    page.title = "极简健身计时器"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.GREY_100
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    # --- 1. 核心状态变量 ---
    def _debug(msg: str):
        print(f"[DEBUG] {msg}", flush=True)

    workout_plan = []  # 存放解析后的任务列表
    current_task_idx = 0
    rest_cancelled = False
    rest_paused = False
    rest_task = None
    is_resting = False

    work_cancelled = False
    work_paused = False
    work_task = None
    is_working = False
    is_manual_resting = False
    is_training_active = False
    
    # 提示音：使用 flet-audio 插件（支持移动端）
    # 部分客户端不支持第三方 Audio 控件，直接禁用以保证界面稳定。
    audio_player = None

    # --- 2. UI 控件 ---
    # 计划存储（本地持久化到客户端）
    STORAGE_KEY = "plans_v1"
    LAST_PLAN_ID_KEY = "last_plan_id_v1"
    prefs = ft.SharedPreferences()

    def _infer_plan_name(text: str):
        return infer_plan_name(text)

    # SharedPreferences service might be unavailable in some runtimes;
    # fall back to in-memory storage to keep app usable.
    plans, last_plan_id, initial_text = await init_plans_state(
        prefs, STORAGE_KEY, LAST_PLAN_ID_KEY
    )

    # 输入框（用户手写或粘贴计划）
    txt_input = ft.TextField(
        multiline=True,
        min_lines=5,
        hint_text="输入格式例如:\n俯卧撑 | 4组 | 力竭 | 休90\n深蹲 | 3组 | 15次 | 休60",
        value=initial_text
    )
    lbl_plan_title = ft.Text(f"当前计划：{_infer_plan_name(initial_text)}", size=18, weight=ft.FontWeight.BOLD)

    def on_input_change(e):
        lbl_plan_title.value = f"当前计划：{_infer_plan_name(txt_input.value or '')}"
        page.update()

    txt_input.on_change = on_input_change

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
    btn_abort_training = ft.Button(
        content="终止本次训练",
        width=220,
        height=44,
        visible=False,
        bgcolor=ft.Colors.RED_600,
        color=ft.Colors.WHITE,
    )

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
        lbl_plan_title.value = f"当前计划：{_infer_plan_name(txt_input.value)}"
        await set_last_plan_id(prefs, LAST_PLAN_ID_KEY, plan_id)
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
        await save_plans(prefs, STORAGE_KEY, plans)
        await set_last_plan_id(prefs, LAST_PLAN_ID_KEY, plan_id)
        last_plan_id = plan_id
        _refresh_plan_dropdown(plan_id)
        lbl_plan_title.value = f"当前计划：{name}"
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
        await save_plans(prefs, STORAGE_KEY, plans)
        await set_last_plan_id(prefs, LAST_PLAN_ID_KEY, pid)
        last_plan_id = pid
        _refresh_plan_dropdown(pid)
        lbl_plan_title.value = f"当前计划：{plans[pid]['name']}"
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
            plans["default"] = {"name": "示例计划", "text": default_plan_text()}
        await save_plans(prefs, STORAGE_KEY, plans)
        # choose next selection
        next_id = sorted(plans.keys())[0]
        await set_last_plan_id(prefs, LAST_PLAN_ID_KEY, next_id)
        last_plan_id = next_id
        _refresh_plan_dropdown(next_id)
        await _apply_plan(next_id)
        _debug(f"_delete_plan_confirmed done, next_id={next_id}")

    async def on_delete_plan(e):
        _debug("on_delete_plan triggered -> delete directly")
        await _delete_plan_confirmed()

    btn_delete_plan.on_click = on_delete_plan

    _refresh_plan_dropdown(last_plan_id)

    auto_back_home_after_plan_select = True
    current_tab = "home"
    btn_nav_home = ft.Button(content="首页", width=96, height=44, disabled=True)
    btn_nav_plan = ft.Button(content="计划", width=96, height=44)

    # --- 3. 逻辑函数 ---
    def parse_plan(text):
        return parse_plan_text(text, debug=_debug)

    async def run_work_timer(seconds, rest_seconds_after):
        """动作计时（例如平板支撑 60秒），结束后自动进入休息"""
        nonlocal is_working, work_cancelled, work_paused
        is_working = True
        work_cancelled = False
        work_paused = False

        lbl_work_timer.visible = True
        btn_action.disabled = True
        btn_work_pause.visible = True
        btn_work_stop.visible = True
        btn_work_pause.disabled = False
        btn_work_stop.disabled = False
        btn_work_pause.content = "暂停"
        page.update()

        def _on_work_tick(remaining: int):
            mins, secs = divmod(remaining, 60)
            lbl_work_timer.value = f"{mins:02d}:{secs:02d}"
            page.update()

        canceled = await countdown(
            int(seconds),
            on_tick=_on_work_tick,
            is_cancelled=lambda: work_cancelled,
            is_paused=lambda: work_paused,
        )
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
        page.run_task(run_rest_timer, int(rest_seconds_after))

    async def run_rest_timer(seconds):
        """后台倒计时线程"""
        nonlocal is_resting, rest_cancelled, rest_paused
        is_resting = True
        rest_cancelled = False
        rest_paused = False
        lbl_timer.visible = True
        btn_action.disabled = True # 休息期间禁用按钮防误触
        btn_pause.visible = True
        btn_stop.visible = True
        btn_pause.disabled = False
        btn_stop.disabled = False
        btn_pause.content = "暂停"
        page.update()
        
        def _on_rest_tick(remaining: int):
            i = remaining
            mins, secs = divmod(i, 60)
            lbl_timer.value = f"{mins:02d}:{secs:02d}"
            page.update()

        canceled = await countdown(
            int(seconds),
            on_tick=_on_rest_tick,
            is_cancelled=lambda: rest_cancelled,
            is_paused=lambda: rest_paused,
        )
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
        nonlocal current_task_idx, is_training_active
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
            btn_abort_training.visible = False
            is_training_active = False

    def _next_step_label(just_finished_task: dict) -> str:
        if current_task_idx >= len(workout_plan):
            return "完成训练"
        nxt = workout_plan[current_task_idx]
        return "下一组" if nxt.get("name") == just_finished_task.get("name") else "下一个动作"

    def _reset_to_home_after_abort():
        nonlocal workout_plan, current_task_idx
        nonlocal rest_cancelled, rest_paused, is_resting
        nonlocal work_cancelled, work_paused, is_working
        nonlocal is_manual_resting, is_training_active

        rest_cancelled = True
        rest_paused = False
        work_cancelled = True
        work_paused = False
        is_resting = False
        is_working = False
        is_manual_resting = False
        is_training_active = False
        workout_plan = []
        current_task_idx = 0

        lbl_timer.visible = False
        lbl_work_timer.visible = False
        btn_pause.visible = False
        btn_stop.visible = False
        btn_work_pause.visible = False
        btn_work_stop.visible = False
        btn_pause.disabled = True
        btn_stop.disabled = True
        btn_work_pause.disabled = True
        btn_work_stop.disabled = True
        btn_abort_training.visible = False
        txt_input.visible = True
        btn_action.disabled = False
        btn_action.content = "解析并开始训练"
        lbl_status.value = "已终止"
        lbl_detail.value = "训练已终止，已返回首页。"
        _set_tab("home")
        page.update()

    async def on_btn_click(e):
        nonlocal current_task_idx, workout_plan, work_task, rest_task, is_manual_resting, is_training_active
        
        # 阶段一：首次点击，解析文本
        if btn_action.content == "解析并开始训练" or btn_action.content == "重新开始":
            workout_plan = parse_plan(txt_input.value)
            if not workout_plan:
                lbl_detail.value = "文本格式错误，请检查！"
                page.update()
                return
            
            current_task_idx = 0
            is_manual_resting = False
            is_training_active = True
            txt_input.visible = False # 隐藏输入框，进入专注模式
            btn_action.content = "完成本组，开始休息"
            btn_abort_training.visible = True
            update_ui_for_current_task()
            page.update()
            return

        if is_manual_resting:
            is_manual_resting = False
            if current_task_idx < len(workout_plan):
                btn_action.content = "完成本组，开始休息"
                update_ui_for_current_task()
            else:
                lbl_status.value = "🎉 训练全部完成！"
                lbl_detail.value = "去喝点蛋白粉吧！"
                btn_action.content = "重新开始"
                btn_abort_training.visible = False
                is_training_active = False
            page.update()
            return
            
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
                work_task = page.run_task(
                    run_work_timer,
                    int(tgt["seconds"]),
                    int(task["rest"]),
                )
            else:
                # 次数目标：改为手动流转，不自动进入倒计时
                next_label = _next_step_label(task)
                is_manual_resting = True
                rest_hint = f"建议休息 {int(task.get('rest', 0))} 秒后继续。" if int(task.get("rest", 0)) > 0 else "可直接继续。"
                lbl_status.value = "休息一下"
                lbl_detail.value = f"已完成 {task['name']}，下一步：{next_label}。{rest_hint}"
                btn_action.content = f"继续（{next_label}）"
                page.update()

    # 绑定按钮事件
    btn_action.on_click = on_btn_click

    def on_pause_click(e):
        nonlocal rest_paused
        # toggle pause/resume
        if not is_resting:
            return
        if not rest_paused:
            rest_paused = True
            btn_pause.content = "继续"
        else:
            rest_paused = False
            btn_pause.content = "暂停"
        page.update()

    def on_stop_click(e):
        nonlocal workout_plan, current_task_idx, is_resting, rest_cancelled, rest_paused, is_training_active
        if not is_resting:
            return
        rest_cancelled = True
        rest_paused = False
        workout_plan = []
        current_task_idx = 0
        txt_input.visible = True
        lbl_status.value = "已终止"
        lbl_detail.value = "你可以修改计划并重新开始"
        btn_action.content = "重新开始"
        btn_abort_training.visible = False
        is_training_active = False
        page.update()

    btn_pause.on_click = on_pause_click
    btn_stop.on_click = on_stop_click

    def on_work_pause_click(e):
        nonlocal work_paused
        if not is_working:
            return
        if not work_paused:
            work_paused = True
            btn_work_pause.content = "继续"
        else:
            work_paused = False
            btn_work_pause.content = "暂停"
        page.update()

    def on_work_stop_click(e):
        nonlocal is_working, work_cancelled, work_paused
        if not is_working:
            return
        work_cancelled = True
        work_paused = False
        lbl_work_timer.visible = False
        btn_work_pause.visible = False
        btn_work_stop.visible = False
        btn_action.disabled = False
        is_working = False
        btn_action.content = "完成本组，开始休息"
        page.update()

    async def on_abort_training_click(e):
        if not is_training_active:
            return
        page.dialog = dlg_abort_training
        dlg_abort_training.open = True
        page.update()

    def on_cancel_abort(e):
        dlg_abort_training.open = False
        page.update()

    async def on_confirm_abort(e):
        dlg_abort_training.open = False
        page.update()
        _reset_to_home_after_abort()

    dlg_abort_training = ft.AlertDialog(
        modal=True,
        title=ft.Text("确认终止训练"),
        content=ft.Text("确定要终止本次训练吗？当前进度将不会保留。"),
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("取消", on_click=on_cancel_abort),
            ft.TextButton("确认终止", on_click=on_confirm_abort),
        ],
    )

    btn_abort_training.on_click = on_abort_training_click

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

    home_view = build_home_view(
        lbl_header=ft.Text("自律即自由", size=20, color=ft.Colors.GREY_500),
        lbl_plan_title=lbl_plan_title,
        txt_input=txt_input,
        lbl_status=lbl_status,
        lbl_detail=lbl_detail,
        lbl_timer=lbl_timer,
        lbl_work_timer=lbl_work_timer,
        btn_pause=btn_pause,
        btn_stop=btn_stop,
        btn_work_pause=btn_work_pause,
        btn_work_stop=btn_work_stop,
        btn_action=btn_action,
        btn_abort_training=btn_abort_training,
    )

    cb_auto_back = ft.Checkbox(label="选择历史计划后自动返回首页", value=auto_back_home_after_plan_select)

    def on_auto_back_toggle(e):
        nonlocal auto_back_home_after_plan_select
        auto_back_home_after_plan_select = bool(cb_auto_back.value)
        _debug(f"auto_back_home_after_plan_select={auto_back_home_after_plan_select}")

    cb_auto_back.on_change = on_auto_back_toggle

    plan_view = build_plan_view(
        cb_auto_back=cb_auto_back,
        dd_plans=dd_plans,
        btn_save_plan=btn_save_plan,
        btn_update_plan=btn_update_plan,
        btn_delete_plan=btn_delete_plan,
    )

    # --- 4. 组装页面 ---
    page.add(
        ft.Row(
            controls=[
                build_sidebar(btn_nav_home, btn_nav_plan),
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
