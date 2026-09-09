import calendar
import datetime
import json
import os
import threading
import urllib.request
import flet as ft

# ---------------- 兼容性配置 (适配 Flet 0.86+ 及历史版本) ----------------
# 对齐方式常量兼容：新版类属性为 ft.Alignment.CENTER，旧版为 ft.alignment.center
ALIGN_CENTER = getattr(ft.Alignment, "CENTER", getattr(ft.alignment, "center", ft.Alignment(0, 0)))

# 边框生成函数兼容：新版为 ft.Border.all，旧版为 ft.border.all
border_all = getattr(ft.Border, "all", getattr(ft.border, "all", None))

# 层叠布局模式兼容：新版为 ft.StackFit.EXPAND，旧版兼容为 "expand"
StackFit = getattr(ft, "StackFit", None)
STACK_FIT_EXPAND = getattr(StackFit, "EXPAND", "expand") if StackFit else "expand"

# 图表控件兼容：Flet 0.86+ 图表已抽离为独立库 flet_charts
try:
    # pyrefly: ignore [missing-import]
    from flet_charts import (
        LineChart,
        LineChartData,
        LineChartDataPoint,
        ChartAxis,
        ChartAxisLabel,
        ChartGridLines,
    )
except ImportError:
    LineChart = getattr(ft, "LineChart", None)
    LineChartData = getattr(ft, "LineChartData", None)
    LineChartDataPoint = getattr(ft, "LineChartDataPoint", None)
    ChartAxis = getattr(ft, "ChartAxis", None)
    ChartAxisLabel = getattr(ft, "ChartAxisLabel", None)
    ChartGridLines = getattr(ft, "ChartGridLines", None)

# 节假日与调休数据支持：使用 chinesecalendar 官方权威规范
try:
    # pyrefly: ignore [missing-import]
    import chinese_calendar as cc
except ImportError:
    cc = None

# 法定节假日主日期映射（仅保留元旦、春节、清明、劳动节、端午、中秋、国庆法定节假日，不包含农历、节气与普通纪念日）
STATUTORY_FESTIVALS = {
    datetime.date(2025, 1, 1): "元旦",
    datetime.date(2025, 1, 29): "春节",
    datetime.date(2025, 4, 4): "清明",
    datetime.date(2025, 5, 1): "劳动节",
    datetime.date(2025, 5, 31): "端午",
    datetime.date(2025, 10, 1): "国庆",
    datetime.date(2025, 10, 6): "中秋",
    datetime.date(2026, 1, 1): "元旦",
    datetime.date(2026, 2, 17): "春节",
    datetime.date(2026, 4, 5): "清明",
    datetime.date(2026, 5, 1): "劳动节",
    datetime.date(2026, 6, 19): "端午",
    datetime.date(2026, 9, 25): "中秋",
    datetime.date(2026, 10, 1): "国庆",
    datetime.date(2027, 1, 1): "元旦",
    datetime.date(2027, 2, 6): "春节",
    datetime.date(2027, 4, 5): "清明",
    datetime.date(2027, 5, 1): "劳动节",
    datetime.date(2027, 6, 9): "端午",
    datetime.date(2027, 9, 15): "中秋",
    datetime.date(2027, 10, 1): "国庆",
}

# 预置 2025-2026 调休补班权威数据（源自 chinesecalendar）
FALLBACK_WORKDAYS = {
    # 2025
    datetime.date(2025, 1, 26), datetime.date(2025, 2, 8), datetime.date(2025, 4, 27),
    datetime.date(2025, 9, 28), datetime.date(2025, 10, 11),
    # 2026
    datetime.date(2026, 2, 14), datetime.date(2026, 2, 28), datetime.date(2026, 5, 9),
    datetime.date(2026, 9, 20), datetime.date(2026, 10, 10),
}

# 预置 2025-2026 法定节假日放假权威数据（源自 chinesecalendar）
FALLBACK_HOLIDAYS = {
    # 2025
    datetime.date(2025, 1, 1),
    datetime.date(2025, 1, 28), datetime.date(2025, 1, 29), datetime.date(2025, 1, 30),
    datetime.date(2025, 1, 31), datetime.date(2025, 2, 1), datetime.date(2025, 2, 2),
    datetime.date(2025, 2, 3), datetime.date(2025, 2, 4),
    datetime.date(2025, 4, 4), datetime.date(2025, 4, 5), datetime.date(2025, 4, 6),
    datetime.date(2025, 5, 1), datetime.date(2025, 5, 2), datetime.date(2025, 5, 3),
    datetime.date(2025, 5, 4), datetime.date(2025, 5, 5),
    datetime.date(2025, 5, 31), datetime.date(2025, 6, 1), datetime.date(2025, 6, 2),
    datetime.date(2025, 10, 1), datetime.date(2025, 10, 2), datetime.date(2025, 10, 3),
    datetime.date(2025, 10, 4), datetime.date(2025, 10, 5), datetime.date(2025, 10, 6),
    datetime.date(2025, 10, 7), datetime.date(2025, 10, 8),
    # 2026
    datetime.date(2026, 1, 1), datetime.date(2026, 1, 2), datetime.date(2026, 1, 3),
    datetime.date(2026, 2, 15), datetime.date(2026, 2, 16), datetime.date(2026, 2, 17),
    datetime.date(2026, 2, 18), datetime.date(2026, 2, 19), datetime.date(2026, 2, 20),
    datetime.date(2026, 2, 21), datetime.date(2026, 2, 22), datetime.date(2026, 2, 23),
    datetime.date(2026, 4, 4), datetime.date(2026, 4, 5), datetime.date(2026, 4, 6),
    datetime.date(2026, 5, 1), datetime.date(2026, 5, 2), datetime.date(2026, 5, 3),
    datetime.date(2026, 5, 4), datetime.date(2026, 5, 5),
    datetime.date(2026, 6, 19), datetime.date(2026, 6, 20), datetime.date(2026, 6, 21),
    datetime.date(2026, 9, 25), datetime.date(2026, 9, 26), datetime.date(2026, 9, 27),
    datetime.date(2026, 10, 1), datetime.date(2026, 10, 2), datetime.date(2026, 10, 3),
    datetime.date(2026, 10, 4), datetime.date(2026, 10, 5), datetime.date(2026, 10, 6),
    datetime.date(2026, 10, 7),
}

# ---------------- 在线节假日数据同步与本地缓存机制 ----------------
HOLIDAY_CACHE_FILE = "holiday_cache.json"

def load_holiday_cache() -> dict:
    """加载本地已缓存的节假日与调休数据"""
    if os.path.exists(HOLIDAY_CACHE_FILE):
        try:
            with open(HOLIDAY_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_holiday_cache(cache: dict):
    """保存节假日与调休数据至本地持久化文件"""
    try:
        with open(HOLIDAY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# 全局节假日内存缓存字典与已同步年份集合
holiday_cache = load_holiday_cache()
synced_years = set()
holiday_update_listeners = []

def clean_festival_name(raw_name: str) -> str:
    """提取法定节假日的简短中文名（如‘中秋节’->‘中秋’，过滤纪念日与节气）"""
    if not raw_name:
        return None
    if "休" in raw_name and ("班" in raw_name or "调" in raw_name):
        return None
    for target in ["元旦", "春节", "清明", "劳动节", "端午", "中秋", "国庆"]:
        if target in raw_name:
            return target
    return None

def fetch_year_holidays_from_api(year: int) -> dict:
    """
    从权威开放节假日接口 (timor.tech) 获取指定年份的法定节假日与调休排期
    一旦国家在每年底公布下一年的官方放假公报，接口将自动同步，客户端即可无感获取
    """
    url = f"https://timor.tech/api/holiday/year/{year}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 0 and "holiday" in data:
                    res = {}
                    for mmdd, info in data["holiday"].items():
                        date_str = info.get("date") or f"{year:04d}-{mmdd}"
                        is_holiday = info.get("holiday", True)
                        name = clean_festival_name(info.get("name", ""))
                        # holiday 为 True 代表法定放假（休），False 代表调休上班（班）
                        res[date_str] = {
                            "is_work": not is_holiday,
                            "is_off": is_holiday,
                            "name": name,
                        }
                    return res
    except Exception:
        pass
    return None

def sync_holidays_async(year: int):
    """后台异步静默拉取指定年份的节假日配置，成功后更新本地缓存并刷新日历"""
    if year in synced_years:
        return
    synced_years.add(year)

    def worker():
        api_data = fetch_year_holidays_from_api(year)
        if api_data:
            updated = False
            for d_str, val in api_data.items():
                if holiday_cache.get(d_str) != val:
                    holiday_cache[d_str] = val
                    updated = True
            if updated:
                save_holiday_cache(holiday_cache)
                for listener in holiday_update_listeners:
                    try:
                        listener()
                    except Exception:
                        pass

    threading.Thread(target=worker, daemon=True).start()

def get_holiday_tag_info(year: int, month: int, day: int):
    """
    根据指定日期获取节假日或调休角标与法定节日名：
    采用多层级弹性架构：
    1. 本地网络同步缓存 (holiday_cache.json) -> 具备在线自动更新能力，2027年及以后只要国务院发文即可无感自动生效
    2. chinese_calendar 离线库 (若已安装)
    3. 内置 2025-2027 权威兜底数据集
    4. 自动触发未知年份后台异步静默同步，避免未来年份频繁重发 APK
    返回: (badge_text, badge_color, holiday_name)
    """
    date_key = f"{year:04d}-{month:02d}-{day:02d}"
    d = datetime.date(year, month, day)

    # 触发后台异步静默获取（如果未同步过）
    if year not in synced_years:
        sync_holidays_async(year)

    # 1. 优先使用已缓存的网络同步权威数据
    if date_key in holiday_cache:
        info = holiday_cache[date_key]
        if info.get("is_work"):
            return "班", ft.Colors.ORANGE_800, info.get("name")
        elif info.get("is_off"):
            return "休", ft.Colors.BLUE_600, info.get("name")
        elif info.get("name"):
            return None, None, info.get("name")

    # 2. 次级使用 chinesecalendar 离线库
    is_work = False
    is_off = False
    if cc is not None:
        try:
            if hasattr(cc, "constants") and d in cc.constants.workdays:
                is_work = True
            elif d.weekday() >= 5 and cc.is_workday(d):
                is_work = True
            elif hasattr(cc, "constants") and (d in cc.constants.holidays or cc.is_in_lieu(d)):
                is_off = True
            elif d.weekday() < 5 and cc.is_holiday(d):
                is_off = True
        except Exception:
            pass

    # 3. 内置兜底数据集补充
    if not is_work and not is_off:
        if d in FALLBACK_WORKDAYS:
            is_work = True
        elif d in FALLBACK_HOLIDAYS:
            is_off = True

    # 提取法定节日名称（如“中秋”、“国庆”）
    holiday_name = STATUTORY_FESTIVALS.get(d)

    # 如果到了未公布调休安排的未来年份（如 2027 年国务院发文前），法定节日当天依然稳妥标“休”
    if not is_work and not is_off and holiday_name:
        is_off = True

    if is_work:
        return "班", ft.Colors.ORANGE_800, holiday_name
    elif is_off:
        return "休", ft.Colors.BLUE_600, holiday_name

    return None, None, holiday_name

DATA_FILE = "weight_data.json"

def load_data() -> dict:
    """从本地 JSON 文件读取体重记录数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data: dict):
    """将体重记录数据持久化保存到本地 JSON 文件"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def main(page: ft.Page):
    """
    主界面逻辑入口：
    适配打包为移动端 Android APK 的原生交互体验，构建底部导航栏 (NavigationBar) 双 Tab 架构：
    1. 【日历打卡】：月度日历卡片、月份切换、本月概览、快捷今日打卡卡片及 FAB 悬浮按钮
    2. 【趋势分析】：全局统计指标、时间范围筛选、全宽平滑折线图、打卡明细历史记录列表
    """
    # 针对桌面端开发与预览，自动适配常见手机竖屏比例 (410 x 840)
    try:
        if hasattr(page, "window"):
            page.window.width = 410
            page.window.height = 840
            page.window.resizable = True
        else:
            setattr(page, "window_width", 410)
            setattr(page, "window_height", 840)
            setattr(page, "window_resizable", True)
    except Exception:
        pass

    page.title = "体重管家"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.GREY_50
    page.padding = 0  # 移动端沉浸式卡片布局，内部边距由 SafeArea 及各视图统一协调

    # 加载本地存储的数据
    records = load_data()
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month
    today_str = now.strftime("%Y-%m-%d")

    # 视图状态变量
    current_tab_index = 0  # 0: 日历打卡, 1: 趋势分析
    chart_range_limit = 15  # 折线图筛选范围：7, 15, 0 (0表示全部)

    # ---------------- 统计计算辅助函数 ----------------
    def get_month_stats(year: int, month: int):
        """计算指定年月的统计信息：打卡天数、最新体重、月初至今增减"""
        prefix = f"{year:04d}-{month:02d}-"
        month_keys = sorted([k for k in records.keys() if k.startswith(prefix)])
        if not month_keys:
            return 0, None, None
        count = len(month_keys)
        latest_val = records[month_keys[-1]]
        first_val = records[month_keys[0]]
        diff = round(latest_val - first_val, 1)
        return count, latest_val, diff

    def get_overall_stats():
        """计算全量历史记录的统计数据：当前体重、累计变化、历史最低、历史最高"""
        if not records:
            return None, None, None, None
        sorted_keys = sorted(records.keys())
        cur_val = records[sorted_keys[-1]]
        first_val = records[sorted_keys[0]]
        tot_diff = round(cur_val - first_val, 1)
        weights = list(records.values())
        min_val = min(weights)
        max_val = max(weights)
        return cur_val, tot_diff, min_val, max_val

    # ---------------- 折线图相关构建 ----------------
    def create_line_chart_data(points, **kwargs):
        """兼容新版 flet_charts 与旧版构建折线数据序列"""
        try:
            return LineChartData(points=points, point=True, rounded_stroke_cap=True, **kwargs)
        except TypeError:
            # pyrefly: ignore [unexpected-keyword]
            return LineChartData(data_points=points, stroke_cap_round=True, **kwargs)

    def create_chart_axis(labels=None, interval=None, label_size=None):
        """兼容新版与旧版构建坐标轴"""
        kwargs = {}
        if labels is not None:
            kwargs["labels"] = labels
        if label_size is not None:
            kwargs["label_size"] = label_size
        if interval is not None:
            try:
                return ChartAxis(**kwargs, label_spacing=interval)
            except TypeError:
                # pyrefly: ignore [unexpected-keyword]
                return ChartAxis(**kwargs, labels_interval=interval)
        return ChartAxis(**kwargs)

    def build_line_chart_control():
        """构建自适应折线图控件，支持时间跨度筛选与空数据友好展示"""
        if LineChart is None:
            return ft.Container(
                content=ft.Text("提示：图表组件需要安装 flet-charts (pip install flet-charts)", color=ft.Colors.GREY_600),
                alignment=ALIGN_CENTER,
                height=180
            )

        sorted_keys = sorted(records.keys())
        if chart_range_limit > 0 and len(sorted_keys) > chart_range_limit:
            active_keys = sorted_keys[-chart_range_limit:]
        else:
            active_keys = sorted_keys

        if not active_keys:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.INSIGHTS, size=40, color=ft.Colors.GREY_400),
                        ft.Text("暂无打卡数据，快去记录第一次体重吧", color=ft.Colors.GREY_600, size=13),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                alignment=ALIGN_CENTER,
                height=200
            )

        data_points = []
        x_labels = []
        weights = [records[k] for k in active_keys]

        for idx, date_str in enumerate(active_keys):
            weight = records[date_str]
            data_points.append(LineChartDataPoint(idx, weight))
            short_date = date_str[5:]  # 取 MM-DD
            x_labels.append(
                ChartAxisLabel(
                    value=idx,
                    label=ft.Text(short_date, size=10, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_700)
                )
            )

        if len(active_keys) == 1:
            min_x = -0.5
            max_x = 0.5
        else:
            min_x = -0.2
            max_x = len(active_keys) - 1 + 0.2

        min_w = min(weights)
        max_w = max(weights)
        if min_w == max_w:
            y_min = max(0.0, round(min_w - 2))
            y_max = round(max_w + 2)
        else:
            diff = max_w - min_w
            y_min = max(0.0, round(min_w - max(1.0, diff * 0.2)))
            y_max = round(max_w + max(1.0, diff * 0.2))

        line_series = create_line_chart_data(
            points=data_points,
            stroke_width=3,
            color=ft.Colors.BLUE_600,
            curved=True,
            below_line_bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.BLUE_600),
        )

        grid_lines = ChartGridLines(color=ft.Colors.GREY_200, width=0.8, dash_pattern=[4, 4]) if ChartGridLines else None

        chart = LineChart(
            data_series=[line_series],
            bottom_axis=create_chart_axis(
                labels=x_labels,
                interval=1 if len(active_keys) <= 8 else 2,
                label_size=32,
            ),
            left_axis=create_chart_axis(
                interval=max(1, int((y_max - y_min) / 4)),
                label_size=45,
            ),
            min_y=y_min,
            max_y=y_max,
            min_x=min_x,
            max_x=max_x,
            expand=True,
            height=210,
            interactive=True,
            horizontal_grid_lines=grid_lines,
        )
        return ft.Row(controls=[chart], expand=False)

    # ---------------- 对话框显示与关闭辅助方法 ----------------
    def show_dialog_compat(dlg):
        """兼容新旧版本的对话框弹出方法"""
        if hasattr(page, "show_dialog"):
            page.show_dialog(dlg)
        else:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def close_dialog_compat(dlg):
        """兼容新旧版本的对话框关闭方法"""
        if hasattr(page, "pop_dialog"):
            page.pop_dialog()
        else:
            dlg.open = False
            page.update()

    # ---------------- 体重记录与修改对话框 ----------------
    def open_record_dialog(date_str: str):
        """弹出指定日期的体重添加/编辑/删除对话框（针对手机端适配数字输入法）"""
        existing_val = records.get(date_str, "")
        weight_input = ft.TextField(
            label="体重 (kg)",
            value=str(existing_val) if existing_val else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="例如: 65.5",
            autofocus=True,
        )

        def save_record(e):
            """保存体重数据并刷新界面"""
            val = weight_input.value.strip()
            if val:
                try:
                    records[date_str] = float(val)
                    save_data(records)
                except ValueError:
                    return
            close_dialog_compat(dlg)
            refresh_current_view()

        def delete_record(e):
            """删除指定日期的体重数据并刷新界面"""
            if date_str in records:
                del records[date_str]
                save_data(records)
            close_dialog_compat(dlg)
            refresh_current_view()

        actions = [
            ft.TextButton("取消", on_click=lambda e: close_dialog_compat(dlg)),
            ft.FilledButton("保存", on_click=save_record),
        ]
        if date_str in records:
            actions.insert(0, ft.TextButton("删除", on_click=delete_record, style=ft.ButtonStyle(color=ft.Colors.RED_400)))

        dlg = ft.AlertDialog(
            title=ft.Text(f"记录体重：{date_str}"),
            content=weight_input,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        show_dialog_compat(dlg)

    # ---------------- 手机端风格月度日历网格渲染 ----------------
    def build_calendar(year: int, month: int):
        """生成符合手机日历视觉体验的卡片日历网格"""
        month_matrix = calendar.monthcalendar(year, month)
        weekday_headers = ["一", "二", "三", "四", "五", "六", "日"]

        # 星期标题栏
        header_row = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        w,
                        weight=ft.FontWeight.W_500,
                        size=12,
                        color=ft.Colors.BLUE_500 if idx >= 5 else ft.Colors.GREY_600
                    ),
                    alignment=ALIGN_CENTER,
                    expand=1,
                    height=28,
                )
                for idx, w in enumerate(weekday_headers)
            ],
            spacing=3
        )

        calendar_rows = [header_row]
        for week in month_matrix:
            cols = []
            for day in week:
                if day == 0:
                    cols.append(ft.Container(expand=1, height=54))
                else:
                    date_key = f"{year:04d}-{month:02d}-{day:02d}"
                    has_val = date_key in records
                    weight_display = f"{records[date_key]}k" if has_val else ""

                    badge_text, badge_color, holiday_name = get_holiday_tag_info(year, month, day)
                    date_obj = datetime.date(year, month, day)
                    is_weekend = (date_obj.weekday() >= 5)

                    # 判断是否为当前日期（今天）
                    is_today = (date_key == today_str)

                    # 样式判定规范：
                    # 1. 体重记录日：淡蓝背景，浅蓝强调边框（若恰好为今日则边框加粗加深）
                    # 2. 今日未记录：淡蓝背景，醒目蓝色边框，副文本标注“今天”
                    # 3. 节假日（休）：浅蓝圆角卡片背景，蓝色大数字与节日名称
                    # 4. 调休补班（班）：浅灰圆角卡片背景，黑色大数字
                    # 5. 普通周末：无底色，清爽蓝色大数字
                    # 6. 普通工作日：无底色，深黑色大数字
                    cell_border = None
                    if has_val:
                        bg_color = ft.Colors.BLUE_50
                        cell_border = border_all(2.0 if is_today else 1.2, ft.Colors.BLUE_600 if is_today else ft.Colors.BLUE_300) if border_all else None
                        num_color = ft.Colors.BLUE_900
                        num_weight = ft.FontWeight.BOLD
                        sub_text = weight_display
                        sub_color = ft.Colors.BLUE_700
                        sub_weight = ft.FontWeight.BOLD
                    elif is_today:
                        bg_color = ft.Colors.BLUE_50
                        cell_border = border_all(1.6, ft.Colors.BLUE_500) if border_all else None
                        num_color = ft.Colors.BLUE_700
                        num_weight = ft.FontWeight.BOLD
                        sub_text = holiday_name if holiday_name else ""
                        sub_color = ft.Colors.BLUE_600 if sub_text else ft.Colors.TRANSPARENT
                        sub_weight = ft.FontWeight.W_500
                    elif badge_text == "休":
                        bg_color = ft.Colors.BLUE_50
                        num_color = ft.Colors.BLUE_600
                        num_weight = ft.FontWeight.BOLD
                        sub_text = holiday_name if holiday_name else ""
                        sub_color = ft.Colors.BLUE_600
                        sub_weight = ft.FontWeight.W_500
                    elif badge_text == "班":
                        bg_color = ft.Colors.GREY_100
                        num_color = ft.Colors.GREY_900
                        num_weight = ft.FontWeight.BOLD
                        sub_text = ""
                        sub_color = ft.Colors.TRANSPARENT
                        sub_weight = ft.FontWeight.NORMAL
                    elif is_weekend:
                        bg_color = ft.Colors.TRANSPARENT
                        num_color = ft.Colors.BLUE_500
                        num_weight = ft.FontWeight.W_500
                        sub_text = ""
                        sub_color = ft.Colors.TRANSPARENT
                        sub_weight = ft.FontWeight.NORMAL
                    else:
                        bg_color = ft.Colors.TRANSPARENT
                        num_color = ft.Colors.GREY_900
                        num_weight = ft.FontWeight.W_500
                        sub_text = ""
                        sub_color = ft.Colors.TRANSPARENT
                        sub_weight = ft.FontWeight.NORMAL

                    # 日期数字控件：统一使用文本，高亮完全由单元格卡片的淡蓝底色与蓝色边框呈现，去除内部圆圈
                    num_widget = ft.Text(str(day), size=14, weight=num_weight, color=num_color)

                    col_controls = [num_widget]
                    if sub_text:
                        col_controls.append(
                            ft.Text(sub_text, size=10, weight=sub_weight, color=sub_color)
                        )

                    # 居中层容器：铺满整个单元格卡片，保证日期与副文本绝对居中
                    cell_stack_controls = [
                        ft.Container(
                            content=ft.Column(
                                controls=col_controls,
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=1,
                            ),
                            alignment=ALIGN_CENTER,
                            top=0,
                            bottom=0,
                            left=0,
                            right=0,
                        )
                    ]

                    # 右上角小圆徽标：班为橙色圆点，休为蓝色圆点（固定在单元格真实右上角，杜绝遮挡文字）
                    if badge_text:
                        cell_stack_controls.append(
                            ft.Container(
                                content=ft.Text(badge_text, size=8, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                bgcolor=badge_color,
                                width=15,
                                height=15,
                                border_radius=8,
                                alignment=ALIGN_CENTER,
                                top=3,
                                right=3,
                            )
                        )

                    cell = ft.Container(
                        content=ft.Stack(
                            controls=cell_stack_controls,
                            fit=STACK_FIT_EXPAND,
                            expand=True,
                        ),
                        expand=1,
                        height=54,
                        border_radius=10,
                        bgcolor=bg_color,
                        border=cell_border,
                        on_click=lambda e, d=date_key: open_record_dialog(d),
                    )
                    cols.append(cell)
            calendar_rows.append(ft.Row(controls=cols, spacing=3))

        return ft.Container(
            content=ft.Column(controls=calendar_rows, spacing=4),
            bgcolor=ft.Colors.WHITE,
            padding=ft.Padding(8, 10, 8, 10),
            border=border_all(1, ft.Colors.GREY_200) if border_all else None,
            border_radius=14,
        )

    # ---------------- 视图构建：Tab 1 日历打卡视图 ----------------
    def change_month(delta: int):
        """切换月份并刷新日历打卡视图"""
        nonlocal current_year, current_month
        current_month += delta
        if current_month > 12:
            current_month = 1
            current_year += 1
        elif current_month < 1:
            current_month = 12
            current_year -= 1
        refresh_current_view()

    def jump_to_today():
        """快速返回今天所在的年月"""
        nonlocal current_year, current_month
        current_year = now.year
        current_month = now.month
        refresh_current_view()

    def build_calendar_view():
        """组装移动端【日历打卡】页面内容"""
        is_cur_month = (current_year == now.year and current_month == now.month)

        # 顶部月份切换栏
        month_nav_row = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    icon_color=ft.Colors.GREY_700,
                    tooltip="上一月",
                    on_click=lambda e: change_month(-1),
                ),
                ft.Text(
                    f"{current_year} 年 {current_month} 月",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_900,
                ),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    icon_color=ft.Colors.GREY_700,
                    tooltip="下一月",
                    on_click=lambda e: change_month(1),
                ),
                ft.TextButton(
                    "今",
                    on_click=lambda e: jump_to_today(),
                    visible=not is_cur_month,
                    style=ft.ButtonStyle(
                        color=ft.Colors.BLUE_600,
                        padding=ft.Padding(8, 4, 8, 4),
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # 本月打卡概览卡片
        count, latest_val, diff = get_month_stats(current_year, current_month)
        diff_str = "--"
        diff_color = ft.Colors.GREY_600
        if diff is not None:
            if diff > 0:
                diff_str = f"+{diff} kg"
                diff_color = ft.Colors.RED_500
            elif diff < 0:
                diff_str = f"{diff} kg"
                diff_color = ft.Colors.GREEN_600
            else:
                diff_str = "0.0 kg"

        def build_mini_stat(label: str, val: str, color=ft.Colors.GREY_900):
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(label, size=11, color=ft.Colors.GREY_600),
                        ft.Text(val, size=16, weight=ft.FontWeight.BOLD, color=color),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                expand=1,
            )

        month_stats_card = ft.Container(
            content=ft.Row(
                controls=[
                    build_mini_stat("本月打卡", f"{count} 天"),
                    build_mini_stat("最新体重", f"{latest_val} kg" if latest_val else "--"),
                    build_mini_stat("本月浮动", diff_str, diff_color),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            bgcolor=ft.Colors.WHITE,
            padding=ft.Padding(12, 10, 12, 10),
            border_radius=12,
            border=border_all(1, ft.Colors.GREY_200) if border_all else None,
        )

        # 今日打卡状态提示卡片
        if today_str in records:
            today_card = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_600, size=20),
                        ft.Text(f"今日已打卡：{records[today_str]} kg", size=13, weight=ft.FontWeight.W_500),
                        ft.TextButton("修改", on_click=lambda e: open_record_dialog(today_str)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                bgcolor=ft.Colors.GREEN_50,
                padding=ft.Padding(14, 8, 14, 8),
                border_radius=10,
            )
        else:
            today_card = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.EDIT_CALENDAR, color=ft.Colors.BLUE_600, size=20),
                        ft.Text("今天尚未记录体重", size=13, color=ft.Colors.GREY_800),
                        ft.FilledButton("立即打卡", on_click=lambda e: open_record_dialog(today_str)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                bgcolor=ft.Colors.BLUE_50,
                padding=ft.Padding(14, 8, 14, 8),
                border_radius=10,
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    month_nav_row,
                    month_stats_card,
                    build_calendar(current_year, current_month),
                    today_card,
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding(12, 8, 12, 16),
            expand=True,
        )

    # ---------------- 视图构建：Tab 2 趋势分析视图 ----------------
    def set_chart_filter(limit: int):
        """切换折线图查看时间范围"""
        nonlocal chart_range_limit
        chart_range_limit = limit
        refresh_current_view()

    def build_chart_view():
        """组装移动端【趋势分析】页面内容"""
        cur_w, tot_d, min_w, max_w = get_overall_stats()

        tot_str = "--"
        tot_color = ft.Colors.GREY_600
        if tot_d is not None:
            if tot_d > 0:
                tot_str = f"+{tot_d} kg"
                tot_color = ft.Colors.RED_500
            elif tot_d < 0:
                tot_str = f"{tot_d} kg"
                tot_color = ft.Colors.GREEN_600
            else:
                tot_str = "0.0 kg"

        def build_stat_box(title: str, value: str, val_color=ft.Colors.GREY_900):
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(title, size=11, color=ft.Colors.GREY_600),
                        ft.Text(value, size=15, weight=ft.FontWeight.BOLD, color=val_color),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                expand=1,
            )

        # 整体统计卡片
        overview_card = ft.Container(
            content=ft.Row(
                controls=[
                    build_stat_box("当前体重", f"{cur_w} kg" if cur_w else "--"),
                    build_stat_box("累计增减", tot_str, tot_color),
                    build_stat_box("历史最低", f"{min_w} kg" if min_w else "--"),
                    build_stat_box("历史最高", f"{max_w} kg" if max_w else "--"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            bgcolor=ft.Colors.WHITE,
            padding=ft.Padding(12, 12, 12, 12),
            border_radius=12,
            border=border_all(1, ft.Colors.GREY_200) if border_all else None,
        )

        # 筛选范围按钮
        def create_filter_btn(title: str, limit_val: int):
            is_active = (chart_range_limit == limit_val)
            return ft.Container(
                content=ft.Text(
                    title,
                    size=12,
                    weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                    color=ft.Colors.WHITE if is_active else ft.Colors.GREY_700,
                ),
                bgcolor=ft.Colors.BLUE_600 if is_active else ft.Colors.GREY_100,
                padding=ft.Padding(10, 5, 10, 5),
                border_radius=14,
                on_click=lambda e: set_chart_filter(limit_val),
            )

        filter_row = ft.Row(
            controls=[
                ft.Text("趋势折线", size=15, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        create_filter_btn("近7次", 7),
                        create_filter_btn("近15次", 15),
                        create_filter_btn("全部", 0),
                    ],
                    spacing=6,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # 图表容器卡片
        chart_card = ft.Container(
            content=ft.Column(
                controls=[
                    filter_row,
                    ft.Container(height=6),
                    build_line_chart_control(),
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.WHITE,
            padding=ft.Padding(14, 12, 14, 12),
            border_radius=12,
            border=border_all(1, ft.Colors.GREY_200) if border_all else None,
        )

        # 历史记录明细列表
        sorted_keys = sorted(records.keys(), reverse=True)
        history_items = []
        if not sorted_keys:
            history_items.append(
                ft.Container(
                    content=ft.Text("暂无打卡记录", color=ft.Colors.GREY_500, size=13),
                    alignment=ALIGN_CENTER,
                    padding=16,
                )
            )
        else:
            for d in sorted_keys:
                w_val = records[d]
                history_items.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color=ft.Colors.BLUE_500),
                                        ft.Text(d, size=14, weight=ft.FontWeight.W_500),
                                    ],
                                    spacing=8,
                                ),
                                ft.Row(
                                    controls=[
                                        ft.Text(f"{w_val} kg", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT_OUTLINED,
                                            icon_size=18,
                                            icon_color=ft.Colors.GREY_600,
                                            tooltip="编辑",
                                            on_click=lambda e, date_str=d: open_record_dialog(date_str),
                                        ),
                                    ],
                                    spacing=4,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=ft.Padding(8, 6, 8, 6),
                        border=ft.Border(bottom=ft.BorderSide(0.5, ft.Colors.GREY_200)),
                    )
                )

        history_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("历史打卡明细", size=15, weight=ft.FontWeight.BOLD),
                    ft.Column(controls=history_items, spacing=0),
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.WHITE,
            padding=ft.Padding(14, 12, 14, 12),
            border_radius=12,
            border=border_all(1, ft.Colors.GREY_200) if border_all else None,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    overview_card,
                    chart_card,
                    history_card,
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding(12, 8, 12, 16),
            expand=True,
        )

    # ---------------- 核心导航与刷新控制 ----------------
    appbar_title = ft.Text("日历打卡", size=17, weight=ft.FontWeight.BOLD)
    page.appbar = ft.AppBar(
        title=appbar_title,
        center_title=True,
        bgcolor=ft.Colors.WHITE,
        elevation=0.5,
    )

    main_view_container = ft.Container(content=build_calendar_view(), expand=True)

    def refresh_current_view():
        """刷新当前激活 Tab 的视图展示"""
        if current_tab_index == 0:
            main_view_container.content = build_calendar_view()
        else:
            main_view_container.content = build_chart_view()
        page.update()

    # 注册在线节假日数据更新监听器：网络同步成功后静默自动刷新当前日历
    holiday_update_listeners.append(refresh_current_view)

    def handle_nav_change(e):
        """处理底部导航栏点击切换逻辑"""
        nonlocal current_tab_index
        current_tab_index = e.control.selected_index
        if current_tab_index == 0:
            appbar_title.value = "日历打卡"
        else:
            appbar_title.value = "趋势分析"
        refresh_current_view()

    # 底部导航栏：日历打卡与趋势分析
    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                selected_icon=ft.Icons.CALENDAR_MONTH,
                label="日历打卡",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SHOW_CHART_OUTLINED,
                selected_icon=ft.Icons.SHOW_CHART,
                label="趋势分析",
            ),
        ],
        on_change=handle_nav_change,
        bgcolor=ft.Colors.WHITE,
        elevation=8,
    )

    # 快捷悬浮打卡按钮（移动端圆形加号按钮）
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        tooltip="记今天",
        bgcolor=ft.Colors.BLUE_600,
        foreground_color=ft.Colors.WHITE,
        on_click=lambda e: open_record_dialog(today_str),
    )

    # 使用 SafeArea 包裹主界面，全面兼容 Android 手机屏幕打孔、刘海屏及底部手势黑条
    page.add(
        ft.SafeArea(content=main_view_container, expand=True)
    )

if __name__ == "__main__":
    # 启动应用：新版 Flet 使用 ft.run(main)，旧版向下兼容 ft.app(target=main)
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)