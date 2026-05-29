import sys
import os
import shutil
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QListWidgetItem, QLabel, 
                             QLineEdit, QFileDialog, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# 获取打包后临时释放的资源路径
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 快速检查文件是否生成成功且有效（不再使用 time.sleep 导致卡顿）
def check_file_valid(filepath):
    if os.path.exists(filepath):
        try:
            # 确保文件大小大于1KB，说明不是空文件
            if os.path.getsize(filepath) > 1024:
                return True
        except OSError:
            pass
    return False

# 自定义列表行 UI 控件
class SongItemWidget(QWidget):
    def __init__(self, filename, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 6, 15, 6)
        
        # 歌曲名称（居左）
        self.name_label = QLabel(filename)
        self.name_label.setFont(QFont('Microsoft YaHei', 9))
        self.name_label.setStyleSheet("color: #2C3E50; background: transparent;")
        
        # 状态提示（居右）
        self.status_label = QLabel("待转换")
        self.status_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self.status_label.setStyleSheet("color: #7F8C8D; background: transparent;")
        
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        self.setStyleSheet("background: transparent;")
        
    def set_success(self):
        self.status_label.setText("已转换")
        self.status_label.setStyleSheet("color: #2ECC71; font-weight: bold; background: transparent;") # 绿色UI
        
    def set_failed(self, reason=""):
        self.status_label.setText("转换失败")
        self.status_label.setStyleSheet("color: #E74C3C; font-weight: bold; background: transparent;") # 红色UI
        if reason:
            self.status_label.setToolTip(reason)

class NcmConverterUI(QWidget):
    def __init__(self):
        super().__init__()
        self.imported_files = [] 
        self.initUI()

    def initUI(self):
        self.setWindowTitle('NCM格式转换')
        self.resize(600, 500)
        self.setAcceptDrops(True) 

        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 1. 蓝色虚线框容器（直接覆盖整个导入/列表区域）
        self.list_container = QFrame(self)
        self.list_container.setObjectName("ListContainer")
        self.list_container.setStyleSheet("""
            QFrame#ListContainer {
                border: 2px dashed #1E90FF;
                border-radius: 8px;
                background-color: rgba(30, 144, 255, 0.08); /* 8% 透明度的浅蓝色背景 */
            }
        """)
        container_layout = QVBoxLayout(self.list_container)
        container_layout.setContentsMargins(10, 10, 10, 10)

        # 容器内部：未导入文件时的占位提示标签
        self.placeholder_label = QLabel('【拖拽区域】\n请将 NCM 歌曲文件或整个文件夹拖拽到此处导入', self.list_container)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self.placeholder_label.setStyleSheet("color: #1E90FF; background: transparent;")
        container_layout.addWidget(self.placeholder_label)

        # 容器内部：列表控件
        self.song_list_widget = QListWidget(self.list_container)
        self.song_list_widget.setStyleSheet("background: transparent; border: none;")
        self.song_list_widget.setFont(QFont('Microsoft YaHei', 9))
        self.song_list_widget.hide() 
        container_layout.addWidget(self.song_list_widget)

        main_layout.addWidget(self.list_container)

        # 2. 指定导出文件夹
        export_layout = QHBoxLayout()
        self.export_label = QLabel('导出至：', self)
        self.export_label.setFont(QFont('Microsoft YaHei', 10))
        
        self.export_path_input = QLineEdit(self)
        self.export_path_input.setPlaceholderText('请选择转换后的导出目标文件夹...')
        self.export_path_input.setFont(QFont('Microsoft YaHei', 9))
        
        self.browse_btn = QPushButton('选择文件夹', self)
        self.browse_btn.setFont(QFont('Microsoft YaHei', 9))
        self.browse_btn.clicked.connect(self.select_export_path)

        export_layout.addWidget(self.export_label)
        export_layout.addWidget(self.export_path_input)
        export_layout.addWidget(self.browse_btn)
        main_layout.addLayout(export_layout)

        # 3. 底部操作按钮区域（清空列表 + 开始转换）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.clear_btn = QPushButton('清空列表', self)
        self.clear_btn.setFont(QFont('Microsoft YaHei', 11))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_list)
        btn_layout.addWidget(self.clear_btn)

        self.convert_btn = QPushButton('开始转换并导出', self)
        self.convert_btn.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E90FF;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #00BFFF;
            }
        """)
        self.convert_btn.clicked.connect(self.start_conversion)
        btn_layout.addWidget(self.convert_btn)

        btn_layout.setStretch(0, 1)
        btn_layout.setStretch(1, 3)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.add_folder_files(path)
            elif os.path.isfile(path):
                self.add_file(path)

    def add_file(self, file_path):
        if file_path.lower().endswith('.ncm'):
            existing_paths = [info['path'] for info in self.imported_files]
            if file_path not in existing_paths:
                self.placeholder_label.hide()
                self.song_list_widget.show()

                item_widget = SongItemWidget(os.path.basename(file_path))
                list_item = QListWidgetItem(self.song_list_widget)
                list_item.setSizeHint(item_widget.sizeHint())
                
                self.song_list_widget.addItem(list_item)
                self.song_list_widget.setItemWidget(list_item, item_widget)
                
                self.imported_files.append({
                    'path': file_path,
                    'widget': item_widget,
                    'item': list_item
                })

    def add_folder_files(self, folder_path):
        for root, _, files in os.walk(folder_path):
            for file in files:
                self.add_file(os.path.join(root, file))

    def select_export_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目标文件夹")
        if dir_path:
            self.export_path_input.setText(dir_path)

    def clear_list(self):
        self.song_list_widget.clear()
        self.imported_files.clear()
        self.song_list_widget.hide()
        self.placeholder_label.show()

    def start_conversion(self):
        export_dir = self.export_path_input.text().strip()
        if not self.imported_files:
            QMessageBox.warning(self, '提示', '请先拖入歌曲！')
            return
        if not export_dir or not os.path.exists(export_dir):
            QMessageBox.warning(self, '提示', '请先选择有效的导出文件夹！')
            return

        engine_exe = get_resource_path("Ncm转mp3拖一拖.exe")
        
        if not os.path.exists(engine_exe):
            QMessageBox.critical(self, '错误', f'找不到转换引擎：{engine_exe}')
            return

        try:
            # 1. 后台调用转换引擎
            paths_to_convert = [info['path'] for info in self.imported_files]
            cmd = [engine_exe] + paths_to_convert
            subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            
            success_count = 0
            fail_count = 0
            
            # 2. 立即检测转换结果（不进行循环等待）
            for info in self.imported_files:
                ncm_file = info['path']
                widget = info['widget']
                
                dir_name = os.path.dirname(ncm_file)
                base_name = os.path.splitext(os.path.basename(ncm_file))[0]
                
                moved = False
                # 检查输出格式是否存在
                for ext in ['.mp3', '.flac']:
                    converted_file = os.path.join(dir_name, base_name + ext)
                    
                    # 运行完毕后直接判断文件是否存在，无需挂起线程等待
                    if check_file_valid(converted_file):
                        target_file = os.path.join(export_dir, base_name + ext)
                        if os.path.exists(target_file):
                            os.remove(target_file)
                        shutil.move(converted_file, export_dir)
                        widget.set_success() # 成功：右侧显示绿色的“已转换”
                        moved = True
                        success_count += 1
                        break
                
                if not moved:
                    # 失败：右侧瞬间显示红色的“转换失败”，不再转圈等待
                    widget.set_failed("引擎未能成功解密该文件") 
                    fail_count += 1

            QMessageBox.information(
                self, 
                '转换完成', 
                f'转换流程已结束！\n\n成功导出: {success_count} 首\n失败: {fail_count} 首\n\n失败歌曲可能为最新加密格式，请知悉。'
            )
            
        except Exception as e:
            QMessageBox.critical(self, '运行失败', f'运行出错：\n{str(e)}')
            for info in self.imported_files:
                info['widget'].set_failed(str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = NcmConverterUI()
    ex.show()
    sys.exit(app.exec_())