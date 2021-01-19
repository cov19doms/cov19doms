import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout, QLabel, QHBoxLayout, QVBoxLayout, QListWidget, QAbstractItemView, QComboBox, QCheckBox, QAbstractItemView, QLineEdit, QButtonGroup, QRadioButton, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QFrame
from PyQt5.QtGui import QIcon, QPixmap, QMovie, QFontDatabase, QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QRectF, QPoint, pyqtSignal
import pandas as pd
import numpy as np
import pickle
import threading
import shutil
import datetime
import traceback
import json
import os


class PhotoViewer(QGraphicsView):
    photoClicked = pyqtSignal(QPoint)

    def __init__(self):
        super().__init__()
        self._zoom = 0
        self._empty = True
        self.scale_f = 0.3
        self._scene = QGraphicsScene(self)
        self._photo = QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.setFrameShape(QFrame.NoFrame)

    def set_scale_f(self, scale_f):
        if type(scale_f) in (int, float):
            self.scale_f = abs(scale_f)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QGraphicsView.NoDrag)
            self._photo.setPixmap(QPixmap())
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.0 + self.scale_f
                self._zoom += 1
            else:
                factor = 1.0 - self.scale_f
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0

    def toggleDragMode(self):
        if self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.setDragMode(QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            self.photoClicked.emit(QPoint(event.pos()))
        super(PhotoViewer, self).mousePressEvent(event)



class MainWidget(QWidget):
	def __init__(self):
		super().__init__()
		if getattr(sys, 'frozen', False):
			self.dir_name = os.path.abspath(os.path.dirname(sys.executable) + '/../../../')
		else:
			self.dir_name = os.path.dirname(os.path.abspath(__file__))
		config_path = self.dir_name + '/config.json'
		with open(config_path) as f:
			self.config = json.load(f)
		self.download_dir =  self.dir_name + '/downloads'
		self.df_data_path = self.dir_name + '/data/pkl/df_sample_1000_ext.pkl'
		self.tag_data_path = self.dir_name + '/data/pkl/tag_data.pkl'
		self.screenshot_prefix = self.dir_name + '/data/screenshots/'
		font = QFontDatabase.addApplicationFont(self.dir_name + "/font/ipaexg.ttf")
		font_name = QFontDatabase.applicationFontFamilies(font)
		if font_name:
			self.setFont(QFont(font_name[0]))
		self.tag_list = ['-']
		if "tag_data_extra" in self.config:
			self.tag_list += self.config["tag_data_extra"]
		self.initUI()
		self.initData()


	def initData(self):
		self.df = pd.read_pickle(self.df_data_path) # 'id', 'domain', 'tag_shot_path'
		with open(self.tag_data_path, 'rb') as f:
			self.tag_data = pickle.load(f)

		tag_keys = set(self.tag_data.keys())
		self.data_list.clear()
		self.data_list.addItems([f"{l.id}:\t{l.domain.ljust(20) if len(l.domain) <= 20 else l.domain[:18]+'...'}\t{'False' if not (l.id in tag_keys) else ''}" for l in self.df.itertuples()])

		self.data_total = len(self.df)
		self.data_index = 0

		self.finish_rate.setText(f'終了率: {len(tag_keys)/self.data_total*100:.1f}%')

		self.set_data()


	def on_click_data_change(self, type_s):
		d = 1 if type_s =='down' else -1
		self.data_index = (self.data_index + d) % self.data_total
		self.set_data()


	def set_data(self):
		self.currentData = self.df.iloc[self.data_index]
		self.index_total_label.setText(f"{self.data_index + 1}/{self.data_total}")
		self.id_domain_label.setText(f'{self.currentData.id}: {self.currentData.domain}')
		self.set_tag_label()
		i_item = self.data_list.item(self.data_index)
		i_item.setSelected(True)
		self.data_list.scrollToItem(i_item, hint=0)
		self.show_picture()


	def on_click_download(self):
		[b.setEnabled(False) for b in self.button_ls]
		img_path = self.screenshot_prefix + self.currentData.shot_path.rsplit('/', maxsplit=1)[-1]
		shutil.copy(path, self.download_dir)
		[b.setEnabled(True) for b in self.button_ls]


	def set_tag_label(self):
		data_id = self.currentData.id
		if data_id in self.tag_data:
			self.setTagButton(self.tag_data[data_id])
		else:
			self.setTagButton('-')


	def show_picture(self):
		img_path = self.screenshot_prefix + self.currentData.tag_shot_path.rsplit('/', maxsplit=1)[-1]
		
		[b.setEnabled(False) for b in self.button_ls]
		# print('load pixmap')
		pixmap = QPixmap(img_path)
		if pixmap.isNull():
			pixmap = QPixmap(self.dir_name + '/data/gray.png')
			print('failed to load image')
		self.view.setPhoto(pixmap)
		# print('finish load')
		[b.setEnabled(True) for b in self.button_ls]

# self.tag_combo.checkedButton().text()
	def save_tag(self):
		# print(self.tag_combo.currentText())
		data_id = self.currentData.id
		if self.tag_combo.checkedButton().text() != '-':
			self.tag_data[data_id] = self.tag_combo.checkedButton().text()
			# print(f'save: {p_hash} -> {self.tag_combo.currentText()}')
		elif data_id in self.tag_data and self.tag_combo.checkedButton().text() == '-':
			del self.tag_data[data_id]
		tag_keys = set(self.tag_data.keys())
		self.finish_rate.setText(f'終了率: {len(tag_keys)/self.data_total*100:.1f}%')


	def save_tag_data(self):
		shutil.move(self.tag_data_path, f"{self.dir_name}/data/pkl/backup/tag_data-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pkl") # './tag_dict.pkl', f"./old_tag/tag_dict-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pkl"
		with open(self.tag_data_path, 'wb') as f: # ./tag_dict.pkl
			pickle.dump(self.tag_data , f)


	def listMove(self, item):
		self.data_index = item
		self.set_data()

	def onClickedTagButton(self):
		radioBtn = self.sender()
		if radioBtn.isChecked():
			self.tag_place.setText(radioBtn.text())
			self.save_tag()

	def chunks(self, l, n):
		for i in range(0, len(l), n):
			yield l[i:i + n]


	def setTagButton(self, text):
		for b in self.tag_combo.buttons():
			if b.text() == text:
				b.setChecked(True)
				return
		raise RuntimeError('no such a tag: %s' % text)

	def display_image(self, img):
		self.scene.clear()
		w, h = img.size().width(), img.size().height()
		self.scene.addPixmap(img)
		self.view.fitInView(QRectF(0, 0, w, h), Qt.KeepAspectRatio)
		self.scene.update()


	def initUI(self):
		self.resize(900, 750)
		self.move(100, 100)
		self.setWindowTitle('screenshot tagger')
		self.button_ls = []

		## picture label setting
		#picture
		self.view = PhotoViewer()
		pixmap = QPixmap('gray.png')
		self.view.setPhoto(pixmap)
		if 'scale_factor' in self.config:
			self.view.set_scale_f(self.config['scale_factor'])

		self.view.setFixedWidth(700)
		self.view.setFixedHeight(700)


		## id_domain label
		self.id_domain_label = QLabel("id: domain")
		# self.id_domain_label.setFixedWidth(700)
		self.id_domain_label.setWordWrap(True)

		## tag display
		tag_display = QVBoxLayout()
		tag_display_1 = QHBoxLayout()
		tag_title = QLabel('Tag: ')
		tag_title.setFixedWidth(30)
		self.tag_place = QLabel('-')
		self.tag_combo = QButtonGroup()
		tag_group = QVBoxLayout()
		for t_g in self.chunks(self.tag_list, 3):
			tag_line = QHBoxLayout()
			for t in t_g:
				bt = QRadioButton(t)
				bt.toggled.connect(self.onClickedTagButton)
				bt.setFixedWidth(120)
				tag_line.addWidget(bt)
				self.tag_combo.addButton(bt)
			tag_group.addLayout(tag_line)

		self.tag_save = QPushButton('save')
		self.tag_save.setFixedWidth(60)
		self.tag_save.clicked.connect(self.save_tag_data)

		tag_display_1.addWidget(tag_title)
		tag_display_1.addWidget(self.tag_place)
		tag_display_1.addWidget(self.tag_save)

		tag_display.addLayout(tag_display_1)
		tag_display.addLayout(tag_group)

		## finish rate
		self.finish_rate = QLabel('終了率: 0%')

		## index display
		self.index_total_label = QLabel('0/0')


		## data_list display
		data_list_display = QVBoxLayout()
		# list
		self.data_list = QListWidget()
		self.data_list.setFixedHeight(300)
		self.data_list.currentRowChanged.connect(self.listMove)
		# buttons
		self.up_button = QPushButton('↑')
		self.down_button = QPushButton('↓')
		self.up_button.setShortcut(Qt.Key_Up)
		self.down_button.setShortcut(Qt.Key_Down)
		self.up_button.clicked.connect(lambda: self.on_click_data_change('up'))
		self.down_button.clicked.connect(lambda: self.on_click_data_change('down'))
		self.button_ls = [self.up_button, self.down_button]

		data_list_display.addWidget(self.up_button)
		data_list_display.addWidget(self.data_list)
		data_list_display.addWidget(self.down_button)

		## right layout
		right_layout = QVBoxLayout()
		right_layout.addWidget(self.id_domain_label)
		right_layout.addLayout(tag_display)
		right_layout.addWidget(self.finish_rate)
		right_layout.addWidget(self.index_total_label)
		right_layout.addLayout(data_list_display)


		# layout
		layout = QHBoxLayout()
		layout.addWidget(self.view)
		layout.addLayout(right_layout)

		self.setLayout(layout)

		# show
		self.show()


if __name__ == '__main__':
	app = QApplication(sys.argv)
	ew = MainWidget()    
	sys.exit(app.exec_())
