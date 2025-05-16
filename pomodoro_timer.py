import sys
import random
import time
import os # Keep os for icon path check
import math
from datetime import datetime, timedelta
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QSpinBox,
                            QSystemTrayIcon, QMenu, QAction, QMessageBox,
                            QGridLayout, QSizePolicy, QGroupBox, QFormLayout,
                            QStyle) # QStyle needed for fallback icon
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QEvent, QSize, QRectF
from PyQt5.QtGui import QIcon, QFont, QPainter, QPen, QColor, QBrush
import pygame

class CircularProgressBar(QWidget):
    """自定义圆形进度条控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.percentage = 0
        self.text = "00:00"
        self.total_text = "总剩余: 00:00:00"

    def setPercentage(self, value):
        self.percentage = value
        self.update()

    def setText(self, text):
        self.text = text
        self.update()

    def setTotalText(self, text):
        self.total_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        size = min(width, height) - 10
        rect = QRectF((width - size) / 2, (height - size) / 2, size, size)
        painter.setPen(QPen(QColor(200, 200, 200), 10))
        painter.drawEllipse(rect)
        if self.percentage > 0:
            painter.setPen(QPen(QColor(76, 175, 80), 10))
            start_angle = 90 * 16
            span_angle = -self.percentage * 360 * 16 / 100
            painter.drawArc(rect, start_angle, span_angle)
        painter.save()
        painter.translate(width / 2, height / 2)
        radius = size / 2 - 5
        for i in range(60):
            if i % 5 == 0:
                painter.setPen(QPen(QColor(50, 50, 50), 2))
                outer_len = radius
                inner_len = radius - 10
            else:
                painter.setPen(QPen(QColor(150, 150, 150), 1))
                outer_len = radius
                inner_len = radius - 5
            angle = i * 6
            x1 = inner_len * math.sin(math.radians(angle))
            y1 = -inner_len * math.cos(math.radians(angle))
            x2 = outer_len * math.sin(math.radians(angle))
            y2 = -outer_len * math.cos(math.radians(angle))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.restore()
        painter.setPen(QColor(10, 10, 10))
        font = QFont("Arial", 28, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text)
        font = QFont("Arial", 13, QFont.Bold)
        painter.setFont(font)
        total_rect = QRectF(
            rect.left(),
            rect.top() + rect.height() * 0.66,
            rect.width(),
            rect.height() * 0.2
        )
        painter.drawText(total_rect, Qt.AlignCenter, self.total_text)


class PomodoroTimer(QMainWindow):
    update_signal = pyqtSignal(str)

    # --- UI Text Constants (Copied from windows version) ---
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
    TRAY_SHOW_ACTION_TEXT = "打开" # Changed from "显示"
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
        pygame.mixer.init()
        try:
            # Direct path for non-Windows version, assumes sounds/icons folders are relative to script
            self.ding_sound = pygame.mixer.Sound("sounds/ding.mp3")
            self.break_sound = pygame.mixer.Sound("sounds/break.mp3")
        except Exception as e:
            print(f"声音文件加载失败: {e}")
            self.ding_sound = None # No winsound fallback for generic version
            self.break_sound = None

        self.min_interval = 3
        self.max_interval = 5
        self.short_break_s = 10
        self.long_break_m = 20
        self.total_work_time_m = 90

        self.is_running = False
        self.timer_thread = None
        self.remaining_time_s = 0
        self.total_elapsed_s = 0
        self.current_work_interval_s = 0

        self.current_timer_phase = self.PHASE_IDLE

        self.overall_start_time_ts = 0
        self.total_target_seconds = 0

        self.init_ui()
        self.init_tray()

    def _get_icon(self, icon_name="icons/clock.png"):
        # Simplified for generic version, no resource_path
        try:
            if os.path.exists(icon_name):
                return QIcon(icon_name)
        except Exception as e:
            print(f"加载图标失败 {icon_name}: {e}")
        # Fallback to a standard Qt icon if custom one fails or not found
        try:
            return QApplication.style().standardIcon(QStyle.SP_ComputerIcon) 
        except Exception:
             return QIcon() # Empty icon as last resort

    def format_total_seconds(self, total_seconds):
        s = int(total_seconds)
        m, s_rem = divmod(s, 60)
        h, m_rem = divmod(m, 60)
        return f"{h:02d}:{m_rem:02d}:{s_rem:02d}"

    def init_ui(self):
        self.setWindowTitle(self.APP_NAME)
        self.setMinimumSize(500, 450)
        self.setWindowIcon(self._get_icon())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(self.APP_NAME)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        main_layout.addWidget(title_label)

        settings_group = QGroupBox(self.SETTINGS_GROUP_TITLE)
        settings_layout = QFormLayout(settings_group)

        self.min_spinbox = QSpinBox(minimum=1, maximum=30, value=self.min_interval, minimumWidth=70)
        self.max_spinbox = QSpinBox(minimum=1, maximum=30, value=self.max_interval, minimumWidth=70)
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(self.min_spinbox)
        interval_layout.addWidget(QLabel(self.TO_LABEL))
        interval_layout.addWidget(self.max_spinbox)
        interval_layout.addWidget(QLabel(self.MINUTES_UNIT_LABEL))
        interval_layout.addStretch(1)
        settings_layout.addRow(self.WORK_INTERVAL_LABEL, interval_layout)

        self.short_break_spinbox = QSpinBox(minimum=5, maximum=60, value=self.short_break_s, singleStep=5, minimumWidth=70)
        short_break_layout = QHBoxLayout()
        short_break_layout.addWidget(self.short_break_spinbox)
        short_break_layout.addWidget(QLabel(self.SECONDS_UNIT_LABEL))
        short_break_layout.addStretch(1)
        settings_layout.addRow(self.SHORT_BREAK_LABEL, short_break_layout)
        
        self.long_break_spinbox = QSpinBox(minimum=5, maximum=60, value=self.long_break_m, singleStep=5, minimumWidth=70)
        long_break_layout = QHBoxLayout()
        long_break_layout.addWidget(self.long_break_spinbox)
        long_break_layout.addWidget(QLabel(self.MINUTES_UNIT_LABEL))
        long_break_layout.addStretch(1)
        settings_layout.addRow(self.LONG_BREAK_LABEL, long_break_layout)

        self.total_time_spinbox = QSpinBox(minimum=10, maximum=240, value=self.total_work_time_m, singleStep=10, minimumWidth=70)
        total_time_layout = QHBoxLayout()
        total_time_layout.addWidget(self.total_time_spinbox)
        total_time_layout.addWidget(QLabel(self.MINUTES_UNIT_LABEL))
        total_time_layout.addStretch(1)
        settings_layout.addRow(self.TOTAL_WORK_TIME_LABEL, total_time_layout)
        
        main_layout.addWidget(settings_group)

        status_group = QGroupBox(self.STATUS_GROUP_TITLE)
        status_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel(self.DISPLAY_IDLE)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 14))
        status_layout.addWidget(self.status_label)

        self.progress_widget = CircularProgressBar()
        status_layout.addWidget(self.progress_widget, 1)
        
        initial_total_s = self.total_work_time_m * 60
        self.progress_widget.setText("00:00")
        self.progress_widget.setTotalText(f"总剩余: {self.format_total_seconds(initial_total_s)}")

        main_layout.addWidget(status_group)

        button_layout = QHBoxLayout()
        self.start_button = QPushButton(self.START_BUTTON_TEXT, minimumHeight=40, font=QFont("Arial", 12))
        self.start_button.clicked.connect(self.start_timer)
        self.stop_button = QPushButton(self.STOP_BUTTON_TEXT, minimumHeight=40, font=QFont("Arial", 12), enabled=False)
        self.stop_button.clicked.connect(self.stop_timer)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)

        self.update_signal.connect(self.update_ui_elements)
        self._set_input_widgets_enabled(True)

    def _set_input_widgets_enabled(self, enabled):
        self.min_spinbox.setEnabled(enabled)
        self.max_spinbox.setEnabled(enabled)
        self.short_break_spinbox.setEnabled(enabled)
        self.long_break_spinbox.setEnabled(enabled)
        self.total_time_spinbox.setEnabled(enabled)

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._get_icon()) # Uses simplified _get_icon
        
        tray_menu = QMenu()
        show_action = QAction(self.TRAY_SHOW_ACTION_TEXT, self, triggered=self.show_window)
        quit_action = QAction(self.TRAY_QUIT_ACTION_TEXT, self, triggered=self.close_application)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
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
        reply = QMessageBox.question(self, self.QUIT_CONFIRM_TITLE, self.QUIT_CONFIRM_MESSAGE,
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                     QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            self.stop_timer_logic()
            self.tray_icon.hide()
            event.accept()
        elif reply == QMessageBox.No:
            event.ignore()
            self.hide()
            if not self.tray_icon.isVisible(): self.tray_icon.show()
            self.tray_icon.showMessage(self.MINIMIZED_TO_TRAY_TITLE, self.MINIMIZED_TO_TRAY_MESSAGE,
                                       QSystemTrayIcon.Information, 2000)
        else:
            event.ignore()

    def close_application(self):
        self.stop_timer_logic()
        self.tray_icon.hide()
        QApplication.quit()

    def start_timer(self):
        self.min_interval = self.min_spinbox.value()
        self.max_interval = self.max_spinbox.value()
        self.short_break_s = self.short_break_spinbox.value()
        self.long_break_m = self.long_break_spinbox.value()
        self.total_work_time_m = self.total_time_spinbox.value()

        if self.min_interval > self.max_interval:
            QMessageBox.warning(self, self.SETTINGS_ERROR_TITLE, self.MIN_MAX_INTERVAL_ERROR_MESSAGE)
            return

        self._set_input_widgets_enabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self.is_running = True
        self.total_elapsed_s = 0
        self.total_target_seconds = self.total_work_time_m * 60
        self.overall_start_time_ts = time.time()
        self.current_timer_phase = self.PHASE_WORKING

        self.timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.timer_thread.start()
        self.update_signal.emit(self.DISPLAY_STARTED)

    def stop_timer_logic(self):
        if self.is_running:
            self.is_running = False

    def stop_timer(self):
        self.stop_timer_logic()
        self._set_input_widgets_enabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.current_timer_phase = self.PHASE_IDLE
        self.progress_widget.setText("00:00")
        self.progress_widget.setPercentage(0)
        current_total_s_setting = self.total_time_spinbox.value() * 60
        self.progress_widget.setTotalText(f"总剩余: {self.format_total_seconds(current_total_s_setting)}")
        self.overall_start_time_ts = 0
        self.total_target_seconds = 0
        self.update_signal.emit(self.DISPLAY_STOPPED)

    def _play_sound(self, sound_object): # Simpler play sound for generic version
        if sound_object:
            try:
                sound_object.play()
            except Exception as e:
                print(f"播放声音失败: {e}")

    def timer_loop(self):
        while self.is_running and self.total_elapsed_s < self.total_work_time_m * 60:
            self.current_timer_phase = self.PHASE_WORKING
            self.current_work_interval_s = random.randint(self.min_interval * 60, self.max_interval * 60)
            self.countdown(self.current_work_interval_s, self.DISPLAY_WORKING)
            if not self.is_running: break
            self._play_sound(self.ding_sound)

            self.current_timer_phase = self.PHASE_SHORT_BREAK
            self.update_signal.emit(self.DISPLAY_PLEASE_REST_SECONDS.format(seconds=self.short_break_s))
            self.countdown(self.short_break_s, self.DISPLAY_SHORT_BREAK)
            if not self.is_running: break
            self._play_sound(self.ding_sound)

            self.total_elapsed_s += self.current_work_interval_s + self.short_break_s

        if self.is_running and self.total_elapsed_s >= self.total_work_time_m * 60:
            self.current_timer_phase = self.PHASE_LONG_BREAK
            self._play_sound(self.break_sound)
            long_break_msg = self.DISPLAY_LONG_BREAK_NOTICE.format(
                total_time_min=self.total_work_time_m,
                long_break_min=self.long_break_m
            )
            self.update_signal.emit(long_break_msg)
            self.tray_icon.showMessage("休息提醒", long_break_msg, QSystemTrayIcon.Information, 5000)
            self.countdown(self.long_break_m * 60, self.DISPLAY_LONG_BREAK)
            if self.is_running:
                 self._play_sound(self.ding_sound)
            
        if self.is_running:
            QTimer.singleShot(0, self.stop_timer)

    def countdown(self, seconds, phase_display_text):
        self.remaining_time_s = seconds
        end_time_ts = time.time() + seconds
        while self.is_running and time.time() < end_time_ts:
            self.remaining_time_s = int(end_time_ts - time.time())
            if self.remaining_time_s < 0: self.remaining_time_s = 0
            mins, secs_rem = divmod(self.remaining_time_s, 60)
            time_str = f"{mins:02d}:{secs_rem:02d}"
            self.update_signal.emit(f"{phase_display_text}: {time_str}")
            time.sleep(0.1)
        if self.is_running and self.remaining_time_s <= 0:
             mins, secs_rem = divmod(0, 60)
             time_str = f"{mins:02d}:{secs_rem:02d}"
             self.update_signal.emit(f"{phase_display_text}: {time_str}")

    @pyqtSlot(str)
    def update_ui_elements(self, status_message):
        self.status_label.setText(status_message)
        if ":" in status_message:
            try:
                time_display_for_progress = status_message.split(": ", 1)[1]
                if len(time_display_for_progress.split(':')) == 2:
                     self.progress_widget.setText(time_display_for_progress)
                else:
                     self.progress_widget.setText("00:00")
            except IndexError:
                 self.progress_widget.setText("00:00")
        elif status_message == self.DISPLAY_STOPPED or status_message == self.DISPLAY_IDLE:
            self.progress_widget.setText("00:00")

        current_phase_total_s = 0
        if self.is_running:
            if self.current_timer_phase == self.PHASE_WORKING:
                current_phase_total_s = self.current_work_interval_s
            elif self.current_timer_phase == self.PHASE_SHORT_BREAK:
                current_phase_total_s = self.short_break_s
            elif self.current_timer_phase == self.PHASE_LONG_BREAK:
                current_phase_total_s = self.long_break_m * 60
            if current_phase_total_s > 0:
                elapsed_s = current_phase_total_s - self.remaining_time_s
                percentage = (elapsed_s / current_phase_total_s) * 100
                self.progress_widget.setPercentage(max(0, min(percentage, 100)))
            else:
                self.progress_widget.setPercentage(0)
        else:
             self.progress_widget.setPercentage(0)
             if self.current_timer_phase == self.PHASE_IDLE:
                current_total_s_setting = self.total_time_spinbox.value() * 60
                self.progress_widget.setTotalText(f"总剩余: {self.format_total_seconds(current_total_s_setting)}")

        if self.is_running and self.overall_start_time_ts > 0:
            elapsed_overall_s = time.time() - self.overall_start_time_ts
            remaining_overall_s = self.total_target_seconds - elapsed_overall_s
            if remaining_overall_s < 0: remaining_overall_s = 0
            self.progress_widget.setTotalText(f"总剩余: {self.format_total_seconds(remaining_overall_s)}")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    try:
        # For generic version, directly use path. Ensure icons/clock.png is available.
        app_icon_path = "icons/clock.png" 
        if os.path.exists(app_icon_path):
            application_icon = QIcon(app_icon_path)
            app.setWindowIcon(application_icon)
        else: # Fallback if custom icon is not found
            app.setWindowIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
    except Exception as e:
        print(f"Failed to set application icon: {e}")
        try:
            app.setWindowIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
        except Exception:
            pass

    timer = PomodoroTimer()
    timer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 