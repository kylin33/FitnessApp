import flet as ft
import time
import threading
from flet_audio import Audio

def main(page: ft.Page):
    page.title = "极简健身计时器"
    page.theme_mode = ft.ThemeMode.DARK # 酷炫暗黑模式
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --- 1. 核心状态变量 ---
    workout_plan = []  # 存放解析后的任务列表
    current_task_idx = 0
    
    # 提示音：使用 flet-audio 插件（支持移动端）
    audio_player = Audio(src="assets/ding.wav", autoplay=False)
    page.overlay.append(audio_player)

    # --- 2. UI 控件 ---
    # 输入框（在这里手写或粘贴你的计划）
    txt_input = ft.TextField(
        multiline=True,
        min_lines=5,
        hint_text="输入格式例如:\n俯卧撑 | 4组 | 力竭 | 休90\n深蹲 | 3组 | 15次 | 休60",
        value="俯卧撑 | 4组 | 力竭 | 休90\n下斜俯卧撑 | 3组 | 15次 | 休60"
    )
    
    # 显示当前状态的大字
    lbl_status = ft.Text("准备开始", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
    lbl_detail = ft.Text("点击下方解析计划", size=20)
    
    # 倒计时显示
    lbl_timer = ft.Text("00:00", size=60, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
    lbl_timer.visible = False

    # 按钮
    btn_action = ft.ElevatedButton("解析并开始训练", width=200, height=50)

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
        lbl_timer.visible = True
        btn_action.disabled = True # 休息期间禁用按钮防误触
        
        for i in range(seconds, -1, -1):
            mins, secs = divmod(i, 60)
            lbl_timer.value = f"{mins:02d}:{secs:02d}"
            page.update()
            time.sleep(1)
            
        # 倒计时结束！震动 (+ 提示音如果可用)
        if getattr(page, "haptic_feedback", None):
            page.haptic_feedback.heavy_impact()  # 触发手机震动（移动端）
        if audio_player:
            audio_player.play()
        
        # 准备进入下一个动作
        lbl_timer.visible = False
        btn_action.disabled = False
        btn_action.text = "完成本组，开始休息"
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
            btn_action.text = "重新开始"

    def on_btn_click(e):
        nonlocal current_task_idx, workout_plan
        
        # 阶段一：首次点击，解析文本
        if btn_action.text == "解析并开始训练" or btn_action.text == "重新开始":
            workout_plan = parse_plan(txt_input.value)
            if not workout_plan:
                lbl_detail.value = "文本格式错误，请检查！"
                page.update()
                return
            
            current_task_idx = 0
            txt_input.visible = False # 隐藏输入框，进入专注模式
            btn_action.text = "完成本组，开始休息"
            update_ui_for_current_task()
            page.update()
            
        # 阶段二：训练中点击，触发休息倒计时
        elif btn_action.text == "完成本组，开始休息":
            task = workout_plan[current_task_idx]
            current_task_idx += 1
            
            lbl_status.value = "休息中..."
            lbl_detail.value = "深呼吸，准备下一组"
            btn_action.text = "倒计时中..."
            
            # 开启新线程跑倒计时，防止UI卡死
            threading.Thread(target=run_rest_timer, args=(task["rest"],), daemon=True).start()

    # 绑定按钮事件
    btn_action.on_click = on_btn_click

    # --- 4. 组装页面 ---
    page.add(
        ft.Text("自律即自由", size=20, color=ft.Colors.GREY_500),
        txt_input,
        ft.Divider(),
        lbl_status,
        lbl_detail,
        lbl_timer,
        ft.Container(height=30), # 占位空隙
        btn_action
    )

# 运行APP
ft.app(target=main)
