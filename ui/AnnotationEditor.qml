// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: editor; objectName: "annotationEditor"
    required property var controller
    property var targetData: ({})
    property string selectedColor: "#ffd54f"
    visible: false; color: "#fbfcf9"
    implicitHeight: 330
    onVisibleChanged: controller.setAnnotationEditorVisible(visible)
    Connections { target: editor.controller; function onAnnotationCommitted() { editor.close(); } }
    function close() { visible=false; }
    readonly property bool canApply: controller.canAnnotate && (targetData.mode==="edit" || commentBody.text.trim().length>0)
    function apply() { if(canApply) controller.commitAnnotation(targetData,commentBody.text,author.text,selectedColor); }
    function compose(data) {
        if(visible) return;
        targetData=data; commentBody.text=data.content || ""; author.text=data.author || "";
        selectedColor=data.color || "#ffd54f"; visible=true; commentBody.forceActiveFocus();
    }
    ScrollView {
        id: editorScroll
        anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: editorScroll.availableWidth; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Text { text: editor.targetData.mode==="reply" ? "답글 작성" : editor.targetData.mode==="edit" ? "메모 수정" : "새 메모"; font.pixelSize: 17; font.weight: Font.DemiBold; color: "#294638"; Layout.fillWidth: true }
                ActionButton { objectName: "cancelComment"; glyph: "close"; hint: "작성 취소 · Esc"; enabled: !editor.controller.busy; onClicked: editor.close() }
            }
            Text { text: (Number(editor.targetData.page || 0)+1)+"페이지 · 문서를 보면서 작성하세요"; color: "#7a8879"; font.pixelSize: 12 }
            TextField { id: author; objectName: "commentAuthor"; Layout.fillWidth: true; placeholderText: "작성자"; selectByMouse: true; enabled: !controller.busy }
            ScrollView {
                Layout.fillWidth: true; Layout.preferredHeight: 160
                TextArea { id: commentBody; objectName: "commentBody"; placeholderText: "메모를 입력하세요"; wrapMode: TextEdit.Wrap; textFormat: TextEdit.PlainText; selectByMouse: true; font.pixelSize: 14; enabled: !controller.busy }
            }
            RowLayout {
                visible: editor.targetData.mode!=="reply"; spacing: 12
                Repeater {
                    model: ["#ffd54f","#8ed7ad","#7dbbe6","#ef9bc0","#bcadff"]
                    delegate: Rectangle { required property string modelData; width: 23; height: 23; radius: 12; color: modelData; border.width: editor.selectedColor.toLowerCase()===modelData ? 2 : 0; border.color: "#37512b"; MouseArea { anchors.fill: parent; enabled: !controller.busy; onClicked: editor.selectedColor=parent.modelData } }
                }
            }
            ActionButton { objectName: "applyComment"; Layout.alignment: Qt.AlignRight; text: editor.targetData.mode==="reply" ? "답글 추가" : "적용"; primary: true; enabled: editor.controller.canAnnotate && (editor.targetData.mode==="edit" || commentBody.text.trim().length>0); onClicked: editor.controller.commitAnnotation(editor.targetData,commentBody.text,author.text,editor.selectedColor) }
        }
    }
}
