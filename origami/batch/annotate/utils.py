from PySide2 import QtGui, QtCore
import numpy as np


class Pens:
	def __init__(self, keys):
		self._pens = dict()

		for i, k in enumerate(keys):
			color = QtGui.QColor.fromHsv(20 + 230 * (i / (1 + len(keys))), 200, 250)
			pen = QtGui.QPen()
			pen.setWidth(10)
			pen.setColor(color)
			pen.setCapStyle(QtCore.Qt.RoundCap)
			self._pens[k] = pen

	def get(self, key):
		return self._pens[key]


def render_separators(pixmap, separators):
	pens = Pens(sorted(p[:2] for p in separators.keys()))

	qp = QtGui.QPainter()
	qp.begin(pixmap)

	try:
		qp.setOpacity(0.75)

		for line_path, separator in separators.items():
			qp.setPen(pens.get(line_path[:2]))

			pts = [QtCore.QPointF(x, y) for x, y in separator.coords]
			qp.drawPolyline(pts)

	finally:
		qp.end()

	return pixmap


def block_hsv(classes):
	for i, c in enumerate(classes):
		yield tuple(c), (255 * (i / (1 + len(classes))), 100, 200)


class LabelBrushes:
	def __init__(self, blocks):
		classes = sorted(list(
			set(x[:2] for x in blocks.keys())))
		brushes = dict()
		for c, hsv in block_hsv(classes):
			brushes[c] = QtGui.QBrush(
				QtGui.QColor.fromHsv(*hsv))
		self._brushes = brushes

	def get_brush(self, block_path):
		classifier, label, block_id = block_path
		return self._brushes[(classifier, label)]


def default_pen(color="black", width=5):
	pen = QtGui.QPen()
	pen.setWidth(width)
	pen.setColor(QtGui.QColor(color))
	pen.setCapStyle(QtCore.Qt.RoundCap)
	return pen


def render_blocks(pixmap, blocks, get_label, brushes=None, matrix=None):
	if brushes is None:
		brushes = LabelBrushes(blocks)

	def point(x, y):
		if matrix is not None:
			x, y = matrix @ np.array([x, y, 1])
		return QtCore.QPointF(x, y)

	qp = QtGui.QPainter()
	qp.begin(pixmap)

	try:
		qp.setOpacity(0.5)

		for block_path, block in blocks.items():
			qp.setBrush(brushes.get_brush(block_path))

			poly = QtGui.QPolygonF()
			for x, y in block.image_space_polygon.exterior.coords:
				poly.append(point(x, y))
			qp.drawPolygon(poly)

		qp.setBrush(QtGui.QBrush(QtGui.QColor("white")))

		font = QtGui.QFont("Arial Narrow", 56, QtGui.QFont.Bold)
		qp.setFont(font)

		fm = QtGui.QFontMetrics(font)

		qp.setPen(default_pen())

		for block_path, block in blocks.items():
			x, y = block.image_space_polygon.centroid.coords[0]
			p = point(x, y)

			qp.setOpacity(0.8)
			qp.drawEllipse(p, 50, 50)

			qp.setOpacity(1)
			# flags=QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter does
			# not work. fix it manually.
			label = get_label(block_path)
			w = fm.horizontalAdvance(label)
			qp.drawText(p.x() - w / 2, p.y() + fm.descent(), label)

	finally:
		qp.end()

	return pixmap


def render_lines(pixmap, lines, get_label):
	classes = sorted(list(set(x[:2] for x in lines.keys())))
	brushes = dict()
	for c, (h, s, v) in block_hsv(classes):
		brushes[c + (0,)] = QtGui.QBrush(
			QtGui.QColor.fromHsv(h, s, v))
		brushes[c + (1,)] = QtGui.QBrush(
			QtGui.QColor.fromHsv(h, s // 2, v))

	qp = QtGui.QPainter()
	qp.begin(pixmap)

	try:
		qp.setOpacity(0.5)
		qp.setPen(default_pen())

		for i, (line_path, line) in enumerate(lines.items()):
			classifier, label, block_id, line_id = line_path
			qp.setBrush(brushes[(classifier, label, i % 2)])

			poly = QtGui.QPolygonF()
			for x, y in line.image_space_polygon.exterior.coords:
				poly.append(QtCore.QPointF(x, y))
			qp.drawPolygon(poly)

			line_info = line.info
			p = np.array(line_info["p"])
			right = np.array(line_info["right"])
			up = np.array(line_info["up"])

			qp.drawPolyline([QtCore.QPointF(*p), QtCore.QPointF(*(p + right))])
			qp.drawPolyline([QtCore.QPointF(*p), QtCore.QPointF(*(p + up))])

	finally:
		qp.end()

	return pixmap