import sys
import random
import time
from datetime import datetime, timedelta
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QSpinBox, 
                            QSystemTrayIcon, QMenu, QAction, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QEvent
from PyQt5.QtGui import QIcon, QFont
import pygame

class PomodoroTimer(QMainWindow):
    update_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # 初始化音频
        pygame.mixer.init()
        
        # 加载声音
        self.ding_sound = pygame.mixer.Sound("sounds/ding.mp3")
        self.break_sound = pygame.mixer.Sound("sounds/break.mp3")
        
        # 设置默认参数
        self.min_interval = 3  # 最小间隔(分钟)
        self.max_interval = 5  # 最大间隔(分钟)
        self.short_break = 10  # 短休息(秒)
        self.long_break = 20   # 长休息(分钟)
        self.total_time = 90   # 总工作时间(分钟)
        
        # 状态变量
        self.is_running = False
        self.timer_thread = None
        self.remaining_time = 0
        self.total_elapsed = 0
        self.current_interval = 0
        
        self.init_ui()
        self.init_tray()
    
    def init_ui(self):
        self.setWindowTitle("专注时钟")
        self.setFixedSize(400, 300)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 标题
        title_label = QLabel("专注时钟")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # 设置区域
        settings_layout = QVBoxLayout()
        
        # 工作间隔设置
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("工作间隔:"))
        
        self.min_spinbox = QSpinBox()
        self.min_spinbox.setRange(1, 30)
        self.min_spinbox.setValue(self.min_interval)
        interval_layout.addWidget(self.min_spinbox)
        
        interval_layout.addWidget(QLabel("到"))
        
        self.max_spinbox = QSpinBox()
        self.max_spinbox.setRange(1, 30)
        self.max_spinbox.setValue(self.max_interval)
        interval_layout.addWidget(self.max_spinbox)
        
        interval_layout.addWidget(QLabel("分钟"))
        settings_layout.addLayout(interval_layout)
        
        # 短休息设置
        short_break_layout = QHBoxLayout()
        short_break_layout.addWidget(QLabel("短休息时间:"))
        self.short_break_spinbox = QSpinBox()
        self.short_break_spinbox.setRange(5, 60)
        self.short_break_spinbox.setValue(self.short_break)
        short_break_layout.addWidget(self.short_break_spinbox)
        short_break_layout.addWidget(QLabel("秒"))
        settings_layout.addLayout(short_break_layout)
        
        # 长休息设置
        long_break_layout = QHBoxLayout()
        long_break_layout.addWidget(QLabel("长休息时间:"))
        self.long_break_spinbox = QSpinBox()
        self.long_break_spinbox.setRange(5, 60)
        self.long_break_spinbox.setValue(self.long_break)
        long_break_layout.addWidget(self.long_break_spinbox)
        long_break_layout.addWidget(QLabel("分钟"))
        settings_layout.addLayout(long_break_layout)
        
        # 总时间设置
        total_time_layout = QHBoxLayout()
        total_time_layout.addWidget(QLabel("总工作时间:"))
        self.total_time_spinbox = QSpinBox()
        self.total_time_spinbox.setRange(10, 240)
        self.total_time_spinbox.setValue(self.total_time)
        total_time_layout.addWidget(self.total_time_spinbox)
        total_time_layout.addWidget(QLabel("分钟"))
        settings_layout.addLayout(total_time_layout)
        
        main_layout.addLayout(settings_layout)
        
        # 状态显示
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 12))
        main_layout.addWidget(self.status_label)
        
        # 倒计时显示
        self.timer_label = QLabel("00:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFont(QFont("Arial", 24, QFont.Bold))
        main_layout.addWidget(self.timer_label)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始")
        self.start_button.clicked.connect(self.start_timer)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_timer)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(button_layout)
        
        # 连接信号
        self.update_signal.connect(self.update_ui)
        
    def init_tray(self):
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon('icons/clock.png'))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # 托盘图标点击事件
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "专注时钟",
            "应用程序已最小化到系统托盘，继续在后台运行",
            QSystemTrayIcon.Information,
            2000
        )
    
    def close_application(self):
        self.stop_timer()
        QApplication.quit()
    
    def start_timer(self):
        # 获取用户设置的值
        self.min_interval = self.min_spinbox.value()
        self.max_interval = self.max_spinbox.value()
        self.short_break = self.short_break_spinbox.value()
        self.long_break = self.long_break_spinbox.value()
        self.total_time = self.total_time_spinbox.value()
        
        # 确保最小值不大于最大值
        if self.min_interval > self.max_interval:
            QMessageBox.warning(self, "设置错误", "最小间隔不能大于最大间隔！")
            return
        
        # 禁用设置项
        self.min_spinbox.setEnabled(False)
        self.max_spinbox.setEnabled(False)
        self.short_break_spinbox.setEnabled(False)
        self.long_break_spinbox.setEnabled(False)
        self.total_time_spinbox.setEnabled(False)
        
        # 更新按钮状态
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # 设置状态
        self.is_running = True
        self.total_elapsed = 0
        
        # 启动计时器线程
        self.timer_thread = threading.Thread(target=self.timer_loop)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        
        # 更新状态
        self.update_signal.emit("已开始")
    
    def stop_timer(self):
        if self.is_running:
            self.is_running = False
            
            # 恢复设置项
            self.min_spinbox.setEnabled(True)
            self.max_spinbox.setEnabled(True)
            self.short_break_spinbox.setEnabled(True)
            self.long_break_spinbox.setEnabled(True)
            self.total_time_spinbox.setEnabled(True)
            
            # 更新按钮状态
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            # 更新状态
            self.update_signal.emit("已停止")
            self.timer_label.setText("00:00")
    
    def timer_loop(self):
        while self.is_running and self.total_elapsed < self.total_time * 60:
            # 随机选择当前间隔
            self.current_interval = random.randint(self.min_interval * 60, self.max_interval * 60)
            
            # 倒计时当前间隔
            self.countdown(self.current_interval, "工作中")
            
            if not self.is_running:
                break
                
            # 播放提示音
            self.ding_sound.play()
            
            # 显示短休息提示
            self.update_signal.emit(f"请休息 {self.short_break} 秒")
            
            # 短休息倒计时
            self.countdown(self.short_break, "短休息")
            
            # 更新总计时
            self.total_elapsed += self.current_interval + self.short_break
            
        # 如果是正常结束（不是被用户停止）
        if self.is_running and self.total_elapsed >= self.total_time * 60:
            # 播放长休息提示音
            self.break_sound.play()
            
            # 显示长休息提示
            self.update_signal.emit(f"90分钟已到！请起来活动并休息 {self.long_break} 分钟")
            
            # 弹出通知
            self.tray_icon.showMessage(
                "休息提醒",
                f"90分钟已到！请起来活动并休息 {self.long_break} 分钟",
                QSystemTrayIcon.Information,
                5000
            )
            
            # 长休息倒计时
            self.countdown(self.long_break * 60, "长休息")
            
            # 重置计时器
            self.stop_timer()
    
    def countdown(self, seconds, mode):
        self.remaining_time = seconds
        end_time = time.time() + seconds
        
        while self.is_running and time.time() < end_time:
            # 计算剩余时间
            self.remaining_time = int(end_time - time.time())
            
            # 更新UI
            mins, secs = divmod(self.remaining_time, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            self.update_signal.emit(f"{mode}: {time_str}")
            
            # 100ms的检查间隔，保持UI响应性
            time.sleep(0.1)
    
    @pyqtSlot(str)
    def update_ui(self, msg):
        self.status_label.setText(msg)
        
        # 更新计时器显示
        mins, secs = divmod(self.remaining_time, 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口时不退出应用
    
    timer = PomodoroTimer()
    timer.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 