from __future__ import annotations

import flet as ft


def build_sidebar(btn_nav_home: ft.Control, btn_nav_plan: ft.Control) -> ft.Container:
    return ft.Container(
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
    )


def build_home_view(
    lbl_header: ft.Control,
    lbl_plan_title: ft.Control,
    txt_input: ft.Control,
    lbl_status: ft.Control,
    lbl_detail: ft.Control,
    lbl_timer: ft.Control,
    lbl_work_timer: ft.Control,
    btn_pause: ft.Control,
    btn_stop: ft.Control,
    btn_work_pause: ft.Control,
    btn_work_stop: ft.Control,
    btn_action: ft.Control,
    btn_abort_training: ft.Control,
) -> ft.Container:
    return ft.Container(
        expand=True,
        visible=True,
        content=ft.Column(
            controls=[
                lbl_header,
                lbl_plan_title,
                txt_input,
                ft.Divider(),
                lbl_status,
                lbl_detail,
                lbl_timer,
                lbl_work_timer,
                ft.Container(height=30),
                ft.Row([btn_pause, btn_stop], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                ft.Row([btn_work_pause, btn_work_stop], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                btn_action,
                btn_abort_training,
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def build_plan_view(
    cb_auto_back: ft.Control,
    dd_plans: ft.Control,
    btn_save_plan: ft.Control,
    btn_update_plan: ft.Control,
    btn_delete_plan: ft.Control,
) -> ft.Container:
    return ft.Container(
        expand=True,
        visible=False,
        content=ft.Column(
            controls=[
                ft.Text("计划管理", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("在这里选择历史计划，或保存/修改/删除计划。", color=ft.Colors.GREY_400),
                cb_auto_back,
                dd_plans,
                ft.Row([btn_save_plan, btn_update_plan], spacing=10),
                ft.Row([btn_delete_plan], spacing=10),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
    )
