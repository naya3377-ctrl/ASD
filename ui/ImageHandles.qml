// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

Item {
    id: imageLayer
    required property var controller
    required property var objects
    required property real factor
    required property real pdfWidth
    required property real pdfHeight
    property bool editing: false
    property string selected: controller.imageFocus.id || ""
    Connections { target: controller; function onStateChanged(){ if(controller.imageFocus.id) imageLayer.selected=controller.imageFocus.id; } }
    Repeater {
        model: imageLayer.editing ? imageLayer.objects : []
        delegate: Rectangle {
            id: box; required property var modelData
            objectName: "imageHandle"+modelData.id
            property var rect: modelData.rect
            property bool moving: false
            property real px: rect[0]; property real py: rect[1]
            property real pw: rect[2]-rect[0]; property real ph: rect[3]-rect[1]
            property bool chosen: imageLayer.selected===modelData.id
            x: (moving ? px : rect[0])*imageLayer.factor; y: (moving ? py : rect[1])*imageLayer.factor
            width: (moving ? pw : rect[2]-rect[0])*imageLayer.factor; height: (moving ? ph : rect[3]-rect[1])*imageLayer.factor
            color: moving ? "#224b9571" : "transparent"; border.color: chosen ? "#377e62" : "#879f8c"; border.width: chosen ? 2 : 1
            function begin() { px=rect[0];py=rect[1];pw=rect[2]-rect[0];ph=rect[3]-rect[1];moving=true;imageLayer.selected=modelData.id; }
            function commit() { var next=[px,py,px+pw,py+ph];moving=false; if(Math.abs(next[0]-rect[0])+Math.abs(next[1]-rect[1])+Math.abs(next[2]-rect[2])+Math.abs(next[3]-rect[3])>.05) controller.transformImage(modelData,next); }
            MouseArea {
                id: move; objectName: "imageMoveArea"+box.modelData.id; anchors.fill: parent; preventStealing: true; enabled: !controller.busy
                cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                property point start; property real ox; property real oy
                onPressed: function(mouse) { box.begin();start=mapToItem(imageLayer,mouse.x,mouse.y);ox=box.px;oy=box.py; }
                onPositionChanged: function(mouse) { if(pressed) { var p=mapToItem(imageLayer,mouse.x,mouse.y);box.px=Math.max(0,Math.min(imageLayer.pdfWidth-box.pw,ox+(p.x-start.x)/imageLayer.factor));box.py=Math.max(0,Math.min(imageLayer.pdfHeight-box.ph,oy+(p.y-start.y)/imageLayer.factor)); } }
                onReleased: box.commit()
                onCanceled: box.moving=false
            }
            Rectangle {
                objectName: "imageResize"+box.modelData.id
                visible: box.chosen; width: 12; height: 12; x: parent.width-6; y: parent.height-6
                color: "white"; border.color: "#377e62"; border.width: 2
                MouseArea {
                    anchors.fill: parent; anchors.margins: -4; preventStealing: true; enabled: !controller.busy; cursorShape: Qt.SizeFDiagCursor
                    property point start; property real ow; property real oh
                    onPressed: function(mouse) { box.begin();start=mapToItem(imageLayer,mouse.x,mouse.y);ow=box.pw;oh=box.ph; }
                    onPositionChanged: function(mouse) { if(pressed) {var p=mapToItem(imageLayer,mouse.x,mouse.y);var scale=Math.max(8/ow,8/oh,1+Math.max((p.x-start.x)/imageLayer.factor/ow,(p.y-start.y)/imageLayer.factor/oh));scale=Math.min(scale,(imageLayer.pdfWidth-box.px)/ow,(imageLayer.pdfHeight-box.py)/oh);box.pw=ow*scale;box.ph=oh*scale;} }
                    onReleased: box.commit()
                    onCanceled: box.moving=false
                }
            }
        }
    }
}
