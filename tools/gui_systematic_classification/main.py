import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout, QLabel, QHBoxLayout, QVBoxLayout, QListWidget, QAbstractItemView, QComboBox, QCheckBox, QAbstractItemView, QLineEdit, QButtonGroup, QRadioButton, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QFrame
from PyQt5.QtGui import QIcon, QPixmap, QMovie, QColor, QBrush
from PyQt5.QtCore import Qt, QRectF, QPoint, pyqtSignal
import pandas as pd
import numpy as np
import pickle
import threading
import shutil
import datetime
import traceback
import json


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
		self.prefix = '/Volumes/sshfs_hpc2' # pictures are here
		self.download_dir = './downloads'
		self.tag_list = ['-', 'error', 'empty', 'hosted', 'park', 'contains']
		config_path = './config.json'
		with open(config_path) as f:
			self.config = json.load(f)
		self.initUI()
		self.initData()
		self.init_contains()


	def initData(self):
		self.loading_label.setMovie(self.gif)
		self.df = pd.read_pickle('./sample_10000.pkl')
		with open('p_hash_group_data.pkl', 'rb') as f:
			self.dict_ls_s = pickle.load(f)
		with open('./tag_dict.pkl', 'rb') as f: # ./tag_dict.pkl
			self.tag_dict = pickle.load(f)

		self.group_index = 0
		self.in_group_index = 0
		self.group_count = len(self.dict_ls_s)
		self.in_group_count = self.dict_ls_s[self.group_index]['size']

		self.hash_list.clear()
		self.hash_list.addItems([f"{l['p-hash']}:\t{l['size']}" for l in self.dict_ls_s])

		i_item = self.hash_list.item(self.group_index)
		i_item.setSelected(True)
		self.hash_list.scrollToItem(i_item, hint=0)
		self.loading_label.clear()


	def on_click_hash_change(self, type_s):
		d = 1 if type_s=='down' else -1
		if self.cb.isChecked():
			self.cb_index = (self.cb_index + d) % len(self.untag_ls)
			self.group_index = self.untag_ls[self.cb_index]
		else:
			self.group_index = (self.group_index + d) % self.group_count
		self.in_group_index = 0
		self.in_group_count = self.dict_ls_s[self.group_index]['size']
		# print('hash_change', type_s, d)
		self.hash_label.setText(self.dict_ls_s[self.group_index]['p-hash'])
		self.group_label.setText(f"{self.group_index + 1}/{self.group_count}")
		self.in_group_label.setText(f"{self.in_group_index + 1}/{self.in_group_count}")
		i_item = self.hash_list.item(self.group_index)
		i_item.setSelected(True)
		self.hash_list.scrollToItem(i_item, hint=0)
		self.set_detail()

	def on_click_picture_change(self, type_s):
		d = 1 if type_s=='next' else -1
		self.in_group_index = (self.in_group_index + d) % self.in_group_count
		self.in_group_label.setText(f"{self.in_group_index + 1}/{self.in_group_count}")
		self.set_detail()

	def on_click_download(self):
		[b.setEnabled(False) for b in self.button_ls]
		d_data = self.dict_ls_s[self.group_index]['data'][self.in_group_index]
		path = self.prefix + self.df.at[d_data['idx'], f"{d_data['type']}_shot_path"]
		shutil.copy(path, self.download_dir)
		[b.setEnabled(True) for b in self.button_ls]

	def init_contains(self):
		self.hash_label.setText(self.dict_ls_s[self.group_index]['p-hash'])
		self.group_label.setText(f"{self.group_index + 1}/{self.group_count}")
		self.in_group_label.setText(f"{self.in_group_index + 1}/{self.in_group_count}")
		self.set_detail()

	def set_detail(self):
		d_data = self.dict_ls_s[self.group_index]['data'][self.in_group_index]
		d_dict = self.df.loc[d_data['idx']].to_dict()
		self.detail_list.clear()
		self.detail_list.addItems([f'{k}:\t{v}' for k, v in d_dict.items()])

		self.set_tag_label()

		self.protocol_type.setText(d_data['type'])
		img_path = self.df.at[d_data['idx'], f"{d_data['type']}_shot_path"]
		self.show_picture(img_path)

	def set_tag_label(self):
		p_hash = self.dict_ls_s[self.group_index]['p-hash']
		if p_hash in self.tag_dict:
			self.setTagButton(self.tag_dict[p_hash])
		else:
			self.setTagButton('-')


	def show_picture(self, path):
		[b.setEnabled(False) for b in self.button_ls]
		pixmap = QPixmap(self.prefix + path)
		if pixmap.isNull():
			pixmap = QPixmap('gray.png')
			print('failed to load image')
		self.view.setPhoto(pixmap)
		self.picture_name_label.setText(path)
		[b.setEnabled(True) for b in self.button_ls]


	def save_tag(self):
		p_hash = self.dict_ls_s[self.group_index]['p-hash']
		if self.tag_combo.checkedButton().text() != '-':
			self.tag_dict[p_hash] = self.tag_combo.checkedButton().text()
		elif p_hash in self.tag_dict and self.tag_combo.checkedButton().text() == '-':
			del self.tag_dict[p_hash]

	def save_tag_dict(self):
		shutil.move('./tag_dict.pkl', f"./old_tag/tag_dict-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pkl") # './tag_dict.pkl'
		with open('./tag_dict.pkl', 'wb') as f: # ./tag_dict.pkl
			pickle.dump(self.tag_dict , f)

	def chunks(self, l, n):
		for i in range(0, len(l), n):
			yield l[i:i + n]

	def changeMode(self, state):
		if state == Qt.Checked: # only mode
			self.cb_combo.setEnabled(False)
			self.cb_index = 0
			if self.cb_combo.currentText() =='-':
				self.untag_ls = [i for i in range(self.group_count) if self.dict_ls_s[i]['p-hash'] not in self.tag_dict]
			else:
				self.untag_ls = [i for i in range(self.group_count) if self.dict_ls_s[i]['p-hash'] in self.tag_dict and self.tag_dict[self.dict_ls_s[i]['p-hash']] == self.cb_combo.currentText()]
			self.group_index = self.untag_ls[(self.cb_index) % len(self.untag_ls)]
			self.in_group_index = 0
			self.in_group_count = self.dict_ls_s[self.group_index]['size']
			self.hash_label.setText(self.dict_ls_s[self.group_index]['p-hash'])
			self.group_label.setText(f"{self.group_index + 1}/{self.group_count}")
			self.in_group_label.setText(f"{self.in_group_index + 1}/{self.in_group_count}")
			i_item = self.hash_list.item(self.group_index)
			i_item.setSelected(True)
			self.hash_list.scrollToItem(i_item, hint=0)
			self.init_contains()
		else: # show all
			self.cb_combo.setEnabled(True)
			self.in_group_index = 0
			self.in_group_count = self.dict_ls_s[self.group_index]['size']
			self.hash_label.setText(self.dict_ls_s[self.group_index]['p-hash'])
			self.group_label.setText(f"{self.group_index + 1}/{self.group_count}")
			self.in_group_label.setText(f"{self.in_group_index + 1}/{self.in_group_count}")
			i_item = self.hash_list.item(self.group_index)
			i_item.setSelected(True)
			self.hash_list.scrollToItem(i_item, hint=0)
			self.init_contains()


	def listMove(self, item):
		if not self.cb.isChecked():
			self.group_index = item
			self.in_group_index = 0
			self.in_group_count = self.dict_ls_s[self.group_index]['size']
			# print('hash_change', type_s, d)
			self.hash_label.setText(self.dict_ls_s[self.group_index]['p-hash'])
			self.group_label.setText(f"{self.group_index + 1}/{self.group_count}")
			self.in_group_label.setText(f"{self.in_group_index + 1}/{self.in_group_count}")
			i_item = self.hash_list.item(self.group_index)
			i_item.setSelected(True)
			self.hash_list.scrollToItem(i_item, hint=0)
			self.set_detail()


	def search_hash(self, text):
		if text != '':
			out = self.hash_list.findItems(text, Qt.MatchContains)
			if out:
				i_item = out[0]
				i_item.setSelected(True)
				self.hash_list.scrollToItem(i_item, hint=0)

	def onClickedTagButton(self):
		radioBtn = self.sender()
		if radioBtn.isChecked():
			self.tag_place.setText(radioBtn.text())
			self.save_tag()

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
		self.setWindowTitle('screenshot browser')
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


		## loading indicator
		self.loading_label = QLabel()
		self.loading_label.setFixedHeight(75)
		self.gif = QMovie('loading.gif')
		self.gif.start()


		## tag checkbox
		cb_hbox = QHBoxLayout()
		self.cb = QCheckBox('Only: ')
		self.cb.stateChanged.connect(self.changeMode)
		self.cb_combo = QComboBox()
		[self.cb_combo.addItem(l) for l in self.tag_list]
		cb_hbox.addWidget(self.cb)
		cb_hbox.addWidget(self.cb_combo)


		## tag display
		tag_display = QVBoxLayout()
		tag_display_1 = QHBoxLayout()
		tag_title = QLabel('Tag: ')
		tag_title.setFixedWidth(30)
		self.tag_place = QLabel('-')
		# self.tag_combo = QComboBox()
		self.tag_combo = QButtonGroup()
		tag_group = QVBoxLayout()
		for t_g in self.chunks(self.tag_list, 3):
			tag_line = QHBoxLayout()
			for t in t_g:
				bt = QRadioButton(t)
				bt.toggled.connect(self.onClickedTagButton)
				tag_line.addWidget(bt)
				self.tag_combo.addButton(bt)
			tag_group.addLayout(tag_line)

		self.tag_save = QPushButton('save')
		self.tag_save.setFixedWidth(60)
		self.tag_save.clicked.connect(self.save_tag_dict)

		tag_display_1.addWidget(tag_title)
		tag_display_1.addWidget(self.tag_place)
		tag_display_1.addWidget(self.tag_save)

		tag_display.addLayout(tag_display_1)
		tag_display.addLayout(tag_group)


		## hash display
		hash_display = QHBoxLayout()

		# label title
		label_title = QVBoxLayout()
		label_title.addWidget(QLabel('p-hash'))
		label_title.addWidget(QLabel('group'))
		label_title.addWidget(QLabel('in-group'))

		# label change
		label_contains = QVBoxLayout()
		# p-hash label
		self.hash_label = QLabel('00000000')
		self.hash_label.setFixedWidth(150)
		label_contains.addWidget(self.hash_label)
		# group label
		self.group_label = QLabel('200')
		self.group_label.setFixedWidth(150)
		label_contains.addWidget(self.group_label)
		# in-group label
		self.in_group_label = QLabel('200')
		self.in_group_label.setFixedWidth(150)
		label_contains.addWidget(self.in_group_label)

		# hash_change_button
		hash_change_button = QVBoxLayout()
		self.hash_up = QPushButton('↑')
		self.hash_down = QPushButton('↓')
		self.hash_up.setShortcut(Qt.Key_Up)
		self.hash_down.setShortcut(Qt.Key_Down)
		self.hash_up.clicked.connect(lambda: self.on_click_hash_change('up'))
		self.hash_down.clicked.connect(lambda: self.on_click_hash_change('down'))
		hash_change_button.addWidget(self.hash_up)
		hash_change_button.addWidget(self.hash_down)
		self.button_ls.append(self.hash_up)
		self.button_ls.append(self.hash_down)

		hash_display.addLayout(hash_change_button)
		hash_display.addLayout(label_title)
		hash_display.addLayout(label_contains)


		## detail list
		self.detail_list = QListWidget()
		self.detail_list.setFixedHeight(230)

		## search hash
		le_search = QLineEdit()
		le_search.textChanged.connect(self.search_hash)

		## hash list
		self.hash_list = QListWidget()
		self.hash_list.currentRowChanged.connect(self.listMove)


		## picture change button
		picture_change_buttons = QHBoxLayout()
		self.download = QPushButton('download')
		self.picture_back = QPushButton('←')
		self.picture_next = QPushButton('→')
		self.download.clicked.connect(lambda: self.on_click_download())
		self.picture_back.clicked.connect(lambda: self.on_click_picture_change('back'))
		self.picture_next.clicked.connect(lambda: self.on_click_picture_change('next'))
		picture_change_buttons.addWidget(self.download)
		picture_change_buttons.addWidget(self.picture_back)
		picture_change_buttons.addWidget(self.picture_next)
		self.button_ls.append(self.download)
		self.button_ls.append(self.picture_back)
		self.button_ls.append(self.picture_next)


		## show type
		self.protocol_type = QLabel()
		self.protocol_type.setFixedWidth(100)


		## picture name label
		self.picture_name_label = QLabel()
		self.picture_name_label.setFixedWidth(700)
		self.picture_name_label.setWordWrap(True)


		## base layout
		vbox_left = QVBoxLayout()
		vbox_left.addWidget(self.protocol_type)
		vbox_left.addWidget(self.picture_name_label)
		# vbox_left.addWidget(self.pictute_label)
		vbox_left.addWidget(self.view)


		vbox_right = QVBoxLayout()
		vbox_right.addWidget(self.loading_label)
		vbox_right.addLayout(cb_hbox)
		vbox_right.addLayout(tag_display)
		vbox_right.addLayout(hash_display)
		vbox_right.addWidget(self.detail_list)
		vbox_right.addWidget(le_search)
		vbox_right.addWidget(self.hash_list)
		vbox_right.addLayout(picture_change_buttons)


		# layout
		layout = QHBoxLayout()
		layout.addLayout(vbox_left)
		layout.addLayout(vbox_right)

		self.setLayout(layout)

		# show
		self.show()


if __name__ == '__main__':
	app = QApplication(sys.argv)
	ew = MainWidget()    
	sys.exit(app.exec_())
