from qgis.PyQt.QtCore import Qt, QRectF
from qgis.PyQt.QtGui import QColor, QTextDocument
from qgis.PyQt.QtWidgets import QAction
from qgis.gui import QgsMapToolEmitPoint, QgsMapCanvasItem
from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
from qgis.utils import iface
import requests

class TextItemPopup(QgsMapCanvasItem):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.document = QTextDocument()
        self.document.setDefaultStyleSheet("body {color: black; background-color: white; padding: 5px;}")
        self.point = QgsPointXY(0, 0)  # Initialize point
        self.setZValue(1000)
        self.hide()  # Initially hidden

    def setText(self, text):
        self.document.setHtml(f"<body>{text}</body>")
        self.update()

    def setPosition(self, point):
        self.point = point
        self.updatePosition()

    def updatePosition(self):
        self.setPos(self.toCanvasCoordinates(self.point))

    def paint(self, painter, option, widget):
        if not self.document.isEmpty():
            painter.setRenderHint(painter.Antialiasing, True)
            painter.setBrush(QColor(255, 255, 255, 230))
            painter.setPen(Qt.black)
            
            doc_size = self.document.size()
            rect = QRectF(0, 0, doc_size.width() + 20, doc_size.height() + 20)
            painter.drawRect(rect)
            
            painter.translate(10, 10)
            self.document.drawContents(painter)

    def boundingRect(self):
        doc_size = self.document.size()
        return QRectF(0, 0, doc_size.width() + 40, doc_size.height() + 40)

class GeologyInfoTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.popup = TextItemPopup(self.canvas)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            self.get_geology_info(point)
        elif event.button() == Qt.RightButton:
            self.popup.hide()

    def deactivate(self):
        self.popup.hide()
        QgsMapToolEmitPoint.deactivate(self)

    def get_geology_info(self, point):
        # Convert point to EPSG:4326
        source_crs = self.canvas.mapSettings().destinationCrs()
        dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
        wgs84_point = transform.transform(point)

        # Make API request
        url = f"https://gbank.gsj.jp/seamless/v2/api/1.0/legend.json?point={wgs84_point.y()},{wgs84_point.x()}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            info_text = f"<b>評価値:</b> {data.get('symbol', 'N/A')}<br>" \
                        f"<b>地質:</b> {data.get('lithology_ja', 'N/A')}<br>" \
                        f"<b>説明:</b> {data.get('formationAge_ja', 'N/A')}"
            
            self.popup.setText(info_text)
            self.popup.setPosition(point)
            self.popup.show()
        else:
            iface.messageBar().pushMessage("エラー", "地質情報の取得に失敗しました", level=2, duration=5)

# ツールの作成と有効化
canvas = iface.mapCanvas()
geology_tool = GeologyInfoTool(canvas)
iface.addToolBarIcon(QAction("地質情報", iface.mainWindow(), triggered=lambda: canvas.setMapTool(geology_tool)))