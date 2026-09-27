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
    readonly property var chosenItem: {
        for (var i=0; i<objects.length; ++i) if (objects[i].id===selected) return objects[i];
        return null;
    }
    function remove(item) { if (item && !controller.busy) { selected=""; controller.deleteImage(item); } }
    // Only the page holding the selection answers, so the key is never ambiguous.
    Shortcut {
        sequences: [StandardKey.Delete, "Backspace"]
        enabled: imageLayer.editing && imageLayer.chosenItem!==null && !imageMenu.visible
        onActivated: imageLayer.remove(imageLayer.chosenItem)
    }
    Menu {
        id: imageMenu; objectName: "imageMenu"
        property var item: null
        MenuItem { objectName: "deleteImageItem"; text: "이미지 삭제"; onTriggered: imageLayer.remove(imageMenu.item) }
        MenuItem { text: "닫기"; onTriggered: imageMenu.close() }
    }
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
            function cancel() { moving=false; }
            function commit() { if(!moving) return; var next=[px,py,px+pw,py+ph];moving=false; if(Math.abs(next[0]-rect[0])+Math.abs(next[1]-rect[1])+Math.abs(next[2]-rect[2])+Math.abs(next[3]-rect[3])>.05) controller.transformImage(modelData,next); }
            MouseArea {
                id: move; objectName: "imageMoveArea"+box.modelData.id; anchors.fill: parent; preventStealing: true; enabled: !controller.busy
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                cursorShape: pressed && box.moving ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                property point start; property real ox; property real oy
                // Right button: cancels a move in progress, otherwise opens the image menu.
                onPressed: function(mouse) {
                    if (mouse.button===Qt.RightButton) {
                        if (box.moving) { box.cancel(); return; }
                        imageLayer.selected=box.modelData.id; imageMenu.item=box.modelData; imageMenu.popup(); return;
                    }
                    box.begin();start=mapToItem(imageLayer,mouse.x,mouse.y);ox=box.px;oy=box.py;forceActiveFocus();
                }
                Keys.onEscapePressed: box.cancel()
                onPositionChanged: function(mouse) { if(pressed && box.moving) { var p=mapToItem(imageLayer,mouse.x,mouse.y);box.px=Math.max(0,Math.min(imageLayer.pdfWidth-box.pw,ox+(p.x-start.x)/imageLayer.factor));box.py=Math.max(0,Math.min(imageLayer.pdfHeight-box.ph,oy+(p.y-start.y)/imageLayer.factor)); } }
                onReleased: function(mouse) { if (mouse.button===Qt.LeftButton) box.commit(); }
                onCanceled: box.cancel()
            }
            // Visible delete button on the selected image.
            Rectangle {
                objectName: "imageDelete"+box.modelData.id
                visible: box.chosen && !box.moving; width: 22; height: 22; radius: 11
                x: parent.width-width/2; y: -height/2
                color: deleteArea.containsMouse ? "#c0392b" : "white"; border.color: "#c0392b"; border.width: 1.5
                Text { anchors.centerIn: parent; text: "✕"; font.pixelSize: 12; font.bold: true; color: deleteArea.containsMouse ? "white" : "#c0392b" }
                MouseArea {
                    id: deleteArea; anchors.fill: parent; anchors.margins: -3; hoverEnabled: true; enabled: !controller.busy
                    cursorShape: Qt.PointingHandCursor; onClicked: imageLayer.remove(box.modelData)
                    ToolTip.visible: containsMouse; ToolTip.delay: 400; ToolTip.text: "이미지 삭제 · Delete"
                }
            }
            Rectangle {
                objectName: "imageResize"+box.modelData.id
                visible: box.chosen; width: 12; height: 12; x: parent.width-6; y: parent.height-6
                color: "white"; border.color: "#377e62"; border.width: 2
                MouseArea {
                    anchors.fill: parent; anchors.margins: -4; preventStealing: true; enabled: !controller.busy; cursorShape: Qt.SizeFDiagCursor
                    property point start; property real ow; property real oh
                    onPressed: function(mouse) { box.begin();start=mapToItem(imageLayer,mouse.x,mouse.y);ow=box.pw;oh=box.ph; }
                    onPositionChanged: function(mouse) { if(pressed && box.moving) {var p=mapToItem(imageLayer,mouse.x,mouse.y);var scale=Math.max(8/ow,8/oh,1+Math.max((p.x-start.x)/imageLayer.factor/ow,(p.y-start.y)/imageLayer.factor/oh));scale=Math.min(scale,(imageLayer.pdfWidth-box.px)/ow,(imageLayer.pdfHeight-box.py)/oh);box.pw=ow*scale;box.ph=oh*scale;} }
                    onReleased: box.commit()
                    onCanceled: box.cancel()
                }
            }
        }
    }
}
