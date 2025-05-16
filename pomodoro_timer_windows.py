import sys
import random
import time
import os
import math
from datetime import datetime, timedelta
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QSpinBox, 
                            QSystemTrayIcon, QMenu, QAction, QMessageBox,
                            QGridLayout, QSizePolicy, QGroupBox, QFormLayout,
                            QStyle)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QEvent, QSize, QRectF
from PyQt5.QtGui import QIcon, QFont, QPainter, QPen, QColor, QBrush
import pygame

# 获取资源路径的辅助函数
def resource_path(relative_path):
    """ 获取资源的绝对路径，支持PyInstaller打包后的路径 """
    try:
        # PyInstaller创建临时文件夹并将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class CircularProgressBar(QWidget):
    """自定义圆形进度条控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)  # 设置最小尺寸以确保有足够空间绘制
        self.percentage = 0
        self.text = "00:00"
        self.total_text = "总剩余: 00:00:00"

    def setPercentage(self, value):
        """设置进度百分比 (0-100)"""
        self.percentage = value
        self.update()  # 触发重绘

    def setText(self, text):
        """设置中心显示的文本"""
        self.text = text
        self.update()

    def setTotalText(self, text):
        """设置总剩余时间文本"""
        self.total_text = text
        self.update()

    def paintEvent(self, event):
        """绘制圆形进度条"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 启用抗锯齿
        
        # 计算绘制区域
        width = self.width()
        height = self.height()
        size = min(width, height) - 10  # 留出一些边距
        rect = QRectF((width - size) / 2, (height - size) / 2, size, size)
        
        # 绘制背景圆圈
        painter.setPen(QPen(QColor(200, 200, 200), 10))
        painter.drawEllipse(rect)
        
        # 绘制进度弧
        if self.percentage > 0:
            painter.setPen(QPen(QColor(76, 175, 80), 10))  # 设置为绿色，可以根据需要调整
            # 计算起始角度和跨度角度，Qt中0度是3点钟方向，逆时针旋转
            start_angle = 90 * 16  # 从12点钟方向开始
            span_angle = -self.percentage * 360 * 16 / 100  # 乘以16是因为Qt使用1/16度单位
            painter.drawArc(rect, start_angle, span_angle)
        
        # 绘制刻度线
        painter.save()
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.translate(width / 2, height / 2)  # 将原点移到中心
        radius = size / 2 - 5  # 略微调整刻度线位置
        
        # 绘制60个细小刻度
        for i in range(60):
            if i % 5 == 0:  # 每5分钟一个大刻度
                painter.setPen(QPen(QColor(50, 50, 50), 2))
                outer = radius
                inner = radius - 10
            else:
                painter.setPen(QPen(QColor(150, 150, 150), 1))
                outer = radius
                inner = radius - 5
            
            angle = i * 6  # 每个刻度6度
            x1 = inner * math.sin(math.radians(angle))
            y1 = -inner * math.cos(math.radians(angle))
            x2 = outer * math.sin(math.radians(angle))
            y2 = -outer * math.cos(math.radians(angle))
            painter.drawLine(x1, y1, x2, y2)
        
        painter.restore()
        
        # 绘制当前时间文本
        painter.setPen(QColor(10, 10, 10))
        font = QFont("Arial", 28, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text)
        
        # 绘制总剩余时间文本 - 向上移动并增加字体粗细
        font = QFont("Arial", 13, QFont.Bold)  # 增加字体粗细和略微增加字号
        painter.setFont(font)
        
        # 在圆形内部绘制总剩余时间，而不是边缘
        # 创建一个比原来更高的矩形区域用于文本绘制
        # 将文本区从底部移上来约20%的圆形高度
        total_rect = QRectF(
            rect.left(), 
            rect.top() + rect.height() * 0.66,  # 从顶部向下移动66%的位置(原来是在底部)
            rect.width(), 
            rect.height() * 0.2  # 高度为圆形高度的20%
        )
        painter.drawText(total_rect, Qt.AlignCenter, self.total_text)

class PomodoroTimer(QMainWindow):
    update_signal = pyqtSignal(str)
    
    # --- UI Text Constants ---
    APP_NAME = "专注时钟"
    SETTINGS_GROUP_TITLE = "时间设置"
    STATUS_GROUP_TITLE = "状态"
    WORK_INTERVAL_LABEL = "工作间隔:"
    TO_LABEL = "到"
    MINUTES_UNIT_LABEL = "分钟"
    SECONDS_UNIT_LABEL = "秒"
    SHORT_BREAK_LABEL = "短休息时间:"
    LONG_BREAK_LABEL = "长休息时间:"
    TOTAL_WORK_TIME_LABEL = "总工作时间:"
    START_BUTTON_TEXT = "开始"
    STOP_BUTTON_TEXT = "停止"
    TRAY_SHOW_ACTION_TEXT = "打开"
    TRAY_QUIT_ACTION_TEXT = "退出"
    QUIT_CONFIRM_TITLE = '退出确认'
    QUIT_CONFIRM_MESSAGE = '确定要退出应用程序吗？\n\n如果您想保持程序在后台运行，请点击"取消"，\n程序将最小化到系统托盘。'
    MINIMIZED_TO_TRAY_TITLE = "专注时钟"
    MINIMIZED_TO_TRAY_MESSAGE = "应用程序已最小化到系统托盘，继续在后台运行"
    SETTINGS_ERROR_TITLE = "设置错误"
    MIN_MAX_INTERVAL_ERROR_MESSAGE = "最小间隔不能大于最大间隔！"
    
    # --- Timer Phases (Internal State) ---
    PHASE_IDLE = "IDLE"
    PHASE_WORKING = "WORKING"
    PHASE_SHORT_BREAK = "SHORT_BREAK"
    PHASE_LONG_BREAK = "LONG_BREAK"

    # --- Display Texts for Phases ---
    DISPLAY_IDLE = "准备就绪"
    DISPLAY_WORKING = "工作中"
    DISPLAY_SHORT_BREAK = "短休息"
    DISPLAY_LONG_BREAK = "长休息"
    DISPLAY_STARTED = "已开始"
    DISPLAY_STOPPED = "已停止"
    DISPLAY_PLEASE_REST_SECONDS = "请休息 {seconds} 秒"
    DISPLAY_LONG_BREAK_NOTICE = "{total_time_min}分钟已到！请起来活动并休息 {long_break_min} 分钟"

    def __init__(self):
        super().__init__()
        
        # 初始化音频
        pygame.mixer.init()
        
        # 加载声音
        try:
            self.ding_sound = pygame.mixer.Sound(resource_path("sounds/ding.mp3"))
            self.break_sound = pygame.mixer.Sound(resource_path("sounds/break.mp3"))
        except Exception as e:
            # 如果声音加载失败，使用系统提示音
            print(f"警告：声音文件加载失败，将使用系统提示音: {e}")
            self.ding_sound = None
            self.break_sound = None
        
        # 设置默认参数
        self.min_interval = 3  # 最小间隔(分钟)
        self.max_interval = 5  # 最大间隔(分钟)
        self.short_break_s = 10  # 短休息(秒)
        self.long_break_m = 20   # 长休息(分钟)
        self.total_work_time_m = 90   # 总工作时间(分钟)
        
        # 状态变量
        self.is_running = False
        self.timer_thread = None
        self.remaining_time_s = 0
        self.total_elapsed_s = 0
        self.current_work_interval_s = 0
        
        # 总时间倒计时相关
        self.overall_start_time_ts = 0
        self.total_target_seconds = 0
        self.total_time_remaining_label = None # 将在 init_ui 中创建
        
        self.current_timer_phase = self.PHASE_IDLE
        
        self.init_ui()
        self.init_tray()
    
    def _get_icon(self, icon_name="icons/clock.png"):
        try:
            path = resource_path(icon_name)
            if os.path.exists(path):
                return QIcon(path)
        except Exception as e:
            print(f"加载图标失败 {icon_name}: {e}")
        return QApplication.style().standardIcon(QStyle.SP_ComputerIcon) # Fallback

    def format_total_seconds(self, total_seconds):
        """将总秒数格式化为 HH:MM:SS 的字符串"""
        s = int(total_seconds)
        m, s_rem = divmod(s, 60)
        h, m_rem = divmod(m, 60)
        return f"{h:02d}:{m_rem:02d}:{s_rem:02d}"
    
    def init_ui(self):
        self.setWindowTitle(self.APP_NAME)
        self.setMinimumSize(500, 450)  # 设置最小尺寸，允许放大
        
        # 设置图标
        try:
            icon_path = resource_path("icons/clock.png")
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                self.setWindowIcon(app_icon)
                print(f"成功设置窗口图标: {icon_path}")
        except Exception as e:
            print(f"设置窗口图标失败: {e}")
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)  # 增加布局间距
        main_layout.setContentsMargins(20, 20, 20, 20)  # 增加边距
        
        # 标题
        title_label = QLabel(self.APP_NAME)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # 设置组 - 使用分组框和表单布局使界面更清晰
        settings_group = QGroupBox(self.SETTINGS_GROUP_TITLE)
        settings_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        settings_layout = QFormLayout(settings_group)
        settings_layout.setVerticalSpacing(10)
        settings_layout.setHorizontalSpacing(15)
        
        # 工作间隔设置
        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        
        self.min_spinbox = QSpinBox(minimum=1, maximum=30, value=self.min_interval, minimumWidth=70)
        self.max_spinbox = QSpinBox(minimum=1, maximum=30, value=self.max_interval, minimumWidth=70)
        interval_layout.addWidget(self.min_spinbox)
        interval_layout.addWidget(QLabel(self.TO_LABEL))
        interval_layout.addWidget(self.max_spinbox)
        interval_layout.addWidget(QLabel(self.MINUTES_UNIT_LABEL))
        interval_layout.addStretch(1)
        settings_layout.addRow(self.WORK_INTERVAL_LABEL, interval_layout)
        
        # 短休息设置
        short_break_widget = QWidget()
        short_break_layout = QHBoxLayout(short_break_widget)
        short_break_layout.setContentsMargins(0, 0, 0, 0)
        
        self.short_break_spinbox = QSpinBox(minimum=5, maximum=60, value=self.short_break_s, singleStep=5, minimumWidth=70)
        short_break_layout.addWidget(self.short_break_spinbox)
        short_break_layout.addWidget(QLabel(self.SECONDS_UNIT_LABEL))
        short_break_layout.addStretch(1)
        settings_layout.addRow(self.SHORT_BREAK_LABEL, short_break_widget)
        
        # 长休息设置
        long_break_widget = QWidget()
        long_break_layout = QHBoxLayout(long_break_widget)
        long_break_layout.setContentsMargins(0, 0, 0, 0)
        
        self.long_break_spinbox = QSpinBox(minimum=5, maximum=60, value=self.long_break_m, singleStep=5, minimumWidth=70)
        long_break_layout.addWidget(self.long_break_spinbox)
        long_break_layout.addWidget(QLabel(self.MINUTES_UNIT_LABEL))
        long_break_layout.addStretch(1)
        settings_layout.addRow(self.LONG_BREAK_LABEL, long_break_widget)
        
        # 总时间设置
        total_time_widget = QWidget()
        total_time_layout = QHBoxLayout(total_time_widget)
        total_time_layout.setContentsMargins(0, 0, 0, 0)
        
        self.total_time_spinbox = QSpinBox(minimum=10, maximum=240, value=self.total_work_time_m, singleStep=10, minimumWidth=70)
        total_time_layout.addWidget(self.total_time_spinbox)
        total_time_layout.addWidget(QLabel(self.MINUTES_UNIT_LABEL))
        total_time_layout.addStretch(1)
        settings_layout.addRow(self.TOTAL_WORK_TIME_LABEL, total_time_layout)
        
        main_layout.addWidget(settings_group)
        
        # 状态显示区域 - 使用框架突出显示
        status_group = QGroupBox(self.STATUS_GROUP_TITLE)
        status_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        status_layout = QVBoxLayout(status_group)
        status_layout.setSpacing(10)
        
        # 状态显示
        self.status_label = QLabel(self.DISPLAY_IDLE)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 14))
        status_layout.addWidget(self.status_label)
        
        # 使用圆形进度条替代原来的倒计时标签
        self.progress_widget = CircularProgressBar()
        status_layout.addWidget(self.progress_widget, 1)  # 给进度条更多空间
        
        # 隐藏原来的倒计时标签，但保留用于内部逻辑
        self.timer_label = QLabel("00:00")
        self.timer_label.hide()
        
        # 隐藏原来的总剩余时间标签，但保留用于内部逻辑
        self.total_time_remaining_label = QLabel(f"总剩余: {self.format_total_seconds(self.total_work_time_m * 60)}")
        self.total_time_remaining_label.hide()
        
        # 设置进度条的初始文本
        self.progress_widget.setText("00:00")
        self.progress_widget.setTotalText(f"总剩余: {self.format_total_seconds(self.total_work_time_m * 60)}")
        
        main_layout.addWidget(status_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        self.start_button = QPushButton(self.START_BUTTON_TEXT, minimumHeight=40, font=QFont("Arial", 12))
        self.start_button.clicked.connect(self.start_timer)
        self.stop_button = QPushButton(self.STOP_BUTTON_TEXT, minimumHeight=40, font=QFont("Arial", 12), enabled=False)
        self.stop_button.clicked.connect(self.stop_timer)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(button_layout)
        
        # 连接信号
        self.update_signal.connect(self.update_ui_elements)
        
        self._set_input_widgets_enabled(True)
        
    def init_tray(self):
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 尝试设置图标
        try:
            icon_path = resource_path("icons/clock.png")
            print(f"尝试加载托盘图标，路径: {icon_path}")
            print(f"该路径是否存在: {os.path.exists(icon_path)}")
            
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.tray_icon.setIcon(icon)
                # 确保窗口图标也设置
                self.setWindowIcon(icon)
                print("成功设置托盘图标")
            else:
                # 尝试使用应用程序默认图标
                app_icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
                self.tray_icon.setIcon(app_icon)
                self.setWindowIcon(app_icon)
                print(f"警告：找不到自定义图标文件，使用系统默认图标")
        except Exception as e:
            print(f"设置托盘图标失败: {e}")
            # 尝试使用系统标准图标
            try:
                app_icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
                self.tray_icon.setIcon(app_icon)
                self.setWindowIcon(app_icon)
            except Exception as e:
                print(f"使用系统标准图标也失败: {e}")
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        show_action = QAction(self.TRAY_SHOW_ACTION_TEXT, self, triggered=self.show_window)
        tray_menu.addAction(show_action)
        
        quit_action = QAction(self.TRAY_QUIT_ACTION_TEXT, self, triggered=self.close_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # 显示托盘图标 - 尝试强制确保显示
        self.tray_icon.show()
        QApplication.processEvents()  # 处理挂起的事件以确保图标显示
        
        # 设置工具提示
        self.tray_icon.setToolTip(self.APP_NAME)
    
    def show_window(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        self.raise_()
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()
    
    def closeEvent(self, event):
        # 询问用户是否真的要退出应用程序
        reply = QMessageBox.question(self, self.QUIT_CONFIRM_TITLE, self.QUIT_CONFIRM_MESSAGE,
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                     QMessageBox.Cancel)
        
        if reply == QMessageBox.Yes:
            # 用户选择退出
            self.stop_timer()
            self.tray_icon.hide()  # 隐藏托盘图标
            event.accept()  # 允许关闭
        elif reply == QMessageBox.No:
            # 用户选择最小化到托盘
            event.ignore()
            self.hide()
            # 确保托盘图标可见
            if not self.tray_icon.isVisible():
                self.tray_icon.show()
            # 显示通知
            self.tray_icon.showMessage(
                self.MINIMIZED_TO_TRAY_TITLE,
                self.MINIMIZED_TO_TRAY_MESSAGE,
                QSystemTrayIcon.Information,
                2000
            )
        else:
            # 用户取消操作
            event.ignore()
    
    def close_application(self):
        # 完全退出应用
        self.stop_timer()
        self.tray_icon.hide()  # 隐藏托盘图标
        QApplication.quit()
    
    def start_timer(self):
        # 获取用户设置的值
        self.min_interval = self.min_spinbox.value()
        self.max_interval = self.max_spinbox.value()
        self.short_break_s = self.short_break_spinbox.value()
        self.long_break_m = self.long_break_spinbox.value()
        self.total_work_time_m = self.total_time_spinbox.value()
        
        # 确保最小值不大于最大值
        if self.min_interval > self.max_interval:
            QMessageBox.warning(self, self.SETTINGS_ERROR_TITLE, self.MIN_MAX_INTERVAL_ERROR_MESSAGE)
            return
        
        # 禁用设置项
        self._set_input_widgets_enabled(False)
        
        # 更新按钮状态
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # 设置状态
        self.is_running = True
        self.total_elapsed_s = 0
        
        # 设置总时间倒计时
        self.total_target_seconds = self.total_work_time_m * 60
        self.overall_start_time_ts = time.time()
        self.total_time_remaining_label.setText(f"总剩余: {self.format_total_seconds(self.total_target_seconds)}")
        
        # 启动计时器线程
        self.timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.timer_thread.start()
        
        # 更新状态
        self.update_signal.emit(self.DISPLAY_STARTED)
    
    def stop_timer(self):
        if self.is_running:
            self.is_running = False
            
            # 恢复设置项
            self._set_input_widgets_enabled(True)
            
            # 更新按钮状态
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            # 更新状态
            self.update_signal.emit(self.DISPLAY_STOPPED)
            self.timer_label.setText("00:00")
            
            # 重置总时间显示以反映当前spinbox中的设置
            current_total_seconds_setting = self.total_time_spinbox.value() * 60
            self.total_time_remaining_label.setText(f"总剩余: {self.format_total_seconds(current_total_seconds_setting)}")
            
            # 重置总计时器内部状态
            self.overall_start_time_ts = 0
            self.total_target_seconds = 0
    
    def _play_sound_with_fallback(self, sound):
        """播放声音，如果声音文件不可用则使用Windows系统声音"""
        if sound is not None:
            try:
                sound.play()
            except Exception:
                # 失败时尝试播放系统提示音
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            # 使用Windows系统提示音
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    
    def timer_loop(self):
        while self.is_running and self.total_elapsed_s < self.total_work_time_m * 60:
            # 随机选择当前间隔
            self.current_work_interval_s = random.randint(self.min_interval * 60, self.max_interval * 60)
            
            # 倒计时当前间隔
            self.countdown(self.current_work_interval_s, self.DISPLAY_WORKING)
            
            if not self.is_running:
                break
                
            # 播放提示音
            self._play_sound_with_fallback(self.ding_sound)
            
            # 显示短休息提示
            self.update_signal.emit(self.DISPLAY_PLEASE_REST_SECONDS.format(seconds=self.short_break_s))
            
            # 短休息倒计时
            self.countdown(self.short_break_s, self.DISPLAY_SHORT_BREAK)
            
            # 短休息结束时播放提示音
            if self.is_running:
                self._play_sound_with_fallback(self.ding_sound)
            
            # 更新总计时
            self.total_elapsed_s += self.current_work_interval_s + self.short_break_s
            
        # 如果是正常结束（不是被用户停止）
        if self.is_running and self.total_elapsed_s >= self.total_work_time_m * 60:
            # 播放长休息提示音
            self._play_sound_with_fallback(self.break_sound)
            
            # 显示长休息提示
            long_break_msg = self.DISPLAY_LONG_BREAK_NOTICE.format(
                total_time_min=self.total_work_time_m, 
                long_break_min=self.long_break_m
            )
            self.update_signal.emit(long_break_msg)
            
            # 弹出通知
            self.tray_icon.showMessage(
                "休息提醒",
                long_break_msg,
                QSystemTrayIcon.Information,
                5000
            )
            
            # 长休息倒计时
            self.countdown(self.long_break_m * 60, self.DISPLAY_LONG_BREAK)
            
            # 长休息结束时播放提示音
            if self.is_running:
                self._play_sound_with_fallback(self.ding_sound)
            
            # 重置计时器
            self.stop_timer()
    
    def countdown(self, seconds, mode):
        self.remaining_time_s = seconds
        end_time_ts = time.time() + seconds
        
        while self.is_running and time.time() < end_time_ts:
            # 计算剩余时间
            self.remaining_time_s = int(end_time_ts - time.time())
            
            # 更新UI
            mins, secs_rem = divmod(self.remaining_time_s, 60)
            time_str = f"{mins:02d}:{secs_rem:02d}"
            self.update_signal.emit(f"{mode}: {time_str}")
            
            # 100ms的检查间隔，保持UI响应性
            time.sleep(0.1)
    
    @pyqtSlot(str)
    def update_ui_elements(self, msg):
        self.status_label.setText(msg)
        
        # 更新计时器显示
        mins, secs = divmod(self.remaining_time_s, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.timer_label.setText(time_str)
        self.progress_widget.setText(time_str)
        
        # 计算并更新进度百分比
        if self.is_running:
            if "工作中" in msg:
                # 工作时间进度
                total_secs = self.current_work_interval_s
                elapsed = total_secs - self.remaining_time_s
                percentage = elapsed / total_secs * 100 if total_secs > 0 else 0
            elif "短休息" in msg:
                # 短休息进度
                total_secs = self.short_break_s
                elapsed = total_secs - self.remaining_time_s
                percentage = elapsed / total_secs * 100 if total_secs > 0 else 0
            elif "长休息" in msg:
                # 长休息进度
                total_secs = self.long_break_m * 60
                elapsed = total_secs - self.remaining_time_s
                percentage = elapsed / total_secs * 100 if total_secs > 0 else 0
            else:
                percentage = 0
                
            self.progress_widget.setPercentage(percentage)
        else:
            self.progress_widget.setPercentage(0)
        
        # 更新总剩余时间显示
        if self.is_running and self.overall_start_time_ts > 0:
            elapsed_overall_seconds = time.time() - self.overall_start_time_ts
            remaining_overall_seconds = self.total_target_seconds - elapsed_overall_seconds
            
            if remaining_overall_seconds < 0:
                remaining_overall_seconds = 0
            
            total_remaining_text = f"总剩余: {self.format_total_seconds(remaining_overall_seconds)}"
            self.total_time_remaining_label.setText(total_remaining_text)
            self.progress_widget.setTotalText(total_remaining_text)
        elif not self.is_running:
            # 如果计时器停止，使用当前spinbox设置的总时间
            current_total_seconds_setting = self.total_time_spinbox.value() * 60
            total_remaining_text = f"总剩余: {self.format_total_seconds(current_total_seconds_setting)}"
            self.progress_widget.setTotalText(total_remaining_text)

    def _set_input_widgets_enabled(self, enabled):
        self.min_spinbox.setEnabled(enabled)
        self.max_spinbox.setEnabled(enabled)
        self.short_break_spinbox.setEnabled(enabled)
        self.long_break_spinbox.setEnabled(enabled)
        self.total_time_spinbox.setEnabled(enabled)

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口时不退出应用
    
    # 设置应用程序图标，以便在任务栏和桌面快捷方式中显示
    try:
        icon_path = resource_path("icons/clock.png")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)
            print(f"成功设置应用程序图标: {icon_path}")
    except Exception as e:
        print(f"设置应用程序图标失败: {e}")
    
    timer = PomodoroTimer()
    timer.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 