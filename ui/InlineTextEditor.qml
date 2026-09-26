// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

Item {
    id: editor; objectName: "inlineEditor"+pageNumber
    required property var session
    required property var controller
    required property real factor
    required property int pageNumber
    property var live: controller.liveEditor
    property bool editing: session.visible && session.targetData.page===pageNumber && session.targetData.mode==="replace"
    property var editData: session.targetData
    property var rect: editData.displayRect || editData.rect || [0,0,1,1]
    property int angle: editData.rotation || 0
    visible: editing; z: 60
    x: (angle===90 || angle===180 ? rect[2] : rect[0])*factor
    y: (angle===180 || angle===270 ? rect[3] : rect[1])*factor
    width: live.width; height: live.height
    scale: factor; rotation: angle; transformOrigin: Item.TopLeft
    function attach() { if(editing && live.ready) {live.attach(input.textDocument,pageNumber);input.forceActiveFocus();} }
    onEditingChanged: if(editing) Qt.callLater(attach)
    Component.onCompleted: Qt.callLater(attach)
    Connections {
        target: editor.live
        function onChanged(){ if(editor.editing && editor.live.ready && !input.bound){ input.bound=true;Qt.callLater(editor.attach); } }
    }
    Image {
        visible: live.ready; source: live.background; cache: false
        width: editData.rect ? editData.rect[2]-editData.rect[0] : 0
        height: editData.rect ? editData.rect[3]-editData.rect[1] : 0
        fillMode: Image.Stretch
    }
    TextArea {
        id: input; objectName: editor.editing ? "replacementText" : "inactiveInlineText"+pageNumber
        property bool bound: false
        visible: editor.live.ready; enabled: !controller.busy && editor.live.ready
        width: editor.live.width; height: Math.max(1,(editor.editData.pageHeight || 1000)-(editor.editData.rect ? editor.editData.rect[1] : 0))
        y: editor.live.offset; padding: 0
        background: Item { }
        renderType: Text.NativeRendering
        textFormat: TextEdit.RichText; wrapMode: TextEdit.Wrap; selectByMouse: true; clip: false
        persistentSelection: true
        onTextChanged: if(editor.editing && bound) session.text=getText(0,length)
        Connections { target: editor.session; function onVisibleChanged(){input.bound=false;if(editor.editing)Qt.callLater(editor.attach);} }
    }
    Rectangle { anchors.fill: parent; color: "transparent"; border.color: live.ready ? "#377e62" : "#bc8746"; border.width: 1.5/editor.factor }
    Rectangle {
        visible: live.ready; width: 8/editor.factor; height: 22/editor.factor
        x: parent.width-width/2; y: parent.height/2-height/2
        color: "white"; border.color: "#377e62"; border.width: 1/editor.factor
        MouseArea {
            anchors.fill: parent; anchors.margins: -4/editor.factor; cursorShape: Qt.SizeHorCursor; preventStealing: true
            property point start; property real oldWidth
            onPressed: function(mouse){start=mapToItem(editor,mouse.x,mouse.y);oldWidth=editor.live.width;}
            onPositionChanged: function(mouse){if(pressed){var point=mapToItem(editor,mouse.x,mouse.y);editor.live.setWidth(oldWidth+point.x-start.x);}}
        }
    }
}
