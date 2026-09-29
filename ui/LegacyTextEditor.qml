// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

Item {
    id: editor; objectName: "legacyTextEditor"+pageNumber
    required property var session
    required property var controller
    required property real factor
    required property int pageNumber
    property bool editing: session.visible && session.targetData.page===pageNumber && session.targetData.mode!=="replace"
    property var editData: session.targetData
    property var rect: editData.displayRect || editData.rect || [0,0,1,1]
    property int angle: editData.mode==="replace" ? (editData.rotation || 0) : 0
    visible: editing
    z: 60
    x: (angle===90 || angle===180 ? rect[2] : rect[0])*factor
    y: (angle===180 || angle===270 ? rect[3] : rect[1])*factor
    width: Math.max(8,(editData.mode==="replace" ? editData.rect[2]-editData.rect[0] : rect[2]-rect[0])*factor)
    height: Math.max(8,session.areaHeight*factor)
    rotation: angle; transformOrigin: Item.TopLeft
    Rectangle { anchors.fill: parent; color: "white"; border.color: Theme.accent; border.width: 2 }
    TextArea {
        id: input; objectName: editor.editing ? "replacementText" : "inactiveInlineText"+pageNumber
        anchors.fill: parent; padding: 0; leftPadding: 1; rightPadding: 1
        background: Item { }
        text: editor.editing ? session.text : ""
        font.family: controller.editorFontFamily || session.fallbackFont
        font.pixelSize: Math.max(1,session.fontSize*editor.factor)
        color: "#"+Number(editor.editData.color===undefined ? 0x202124 : editor.editData.color).toString(16).padStart(6,"0")
        textFormat: TextEdit.PlainText; wrapMode: TextEdit.Wrap; selectByMouse: true; clip: true
        enabled: !controller.busy
        onTextChanged: if(editor.editing && session.text!==text) session.text=text
        Component.onCompleted: if(editor.editing) Qt.callLater(function(){input.forceActiveFocus();})
        Connections { target: editor.session; function onVisibleChanged(){ if(editor.editing) Qt.callLater(function(){input.forceActiveFocus();}); } }
    }
}
