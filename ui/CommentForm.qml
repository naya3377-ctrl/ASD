// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Writing area for a comment draft, shown in place inside the comment list.
ColumnLayout {
    id: form
    required property var draft
    readonly property var colors: ["#ffd54f","#8ed7ad","#7dbbe6","#ef9bc0","#bcadff"]
    spacing: 8
    Component.onCompleted: { body.text = draft.text; author.text = draft.author; body.forceActiveFocus(); }

    Text {
        text: form.draft.mode === "reply" ? "답글 작성" : form.draft.mode === "edit" ? "메모 수정" : "새 메모 · " + (Number(form.draft.targetData.page || 0) + 1) + "쪽"
        font.pixelSize: 13; font.weight: Font.Black; color: Theme.ink
    }
    TextField {
        id: author; objectName: "commentAuthor"; Layout.fillWidth: true
        placeholderText: "작성자"; selectByMouse: true; font.pixelSize: 12; color: Theme.ink
        enabled: !form.draft.controller.busy
        background: Rectangle { color: Theme.field; border.width: Theme.border; border.color: author.activeFocus ? Theme.focusRing : Theme.lineStrong }
        onTextChanged: form.draft.author = text
    }
    ScrollView {
        Layout.fillWidth: true; Layout.preferredHeight: Math.min(180, Math.max(76, body.implicitHeight + 12))
        TextArea {
            id: body; objectName: "commentBody"
            placeholderText: form.draft.mode === "reply" ? "답글을 입력하세요" : "메모를 입력하세요"
            wrapMode: TextEdit.Wrap; textFormat: TextEdit.PlainText; selectByMouse: true
            font.pixelSize: 13; color: Theme.ink; enabled: !form.draft.controller.busy
            background: Rectangle { color: Theme.field; border.width: Theme.border; border.color: body.activeFocus ? Theme.focusRing : Theme.lineStrong }
            onTextChanged: form.draft.text = text
            Keys.onPressed: function(event) {
                if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && (event.modifiers & Qt.ControlModifier)) { form.draft.apply(); event.accepted = true; }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 8
        Repeater {
            model: form.draft.mode === "reply" ? [] : form.colors
            delegate: Rectangle {
                required property string modelData
                width: 18; height: 18; radius: 9; color: modelData
                border.width: form.draft.selectedColor.toLowerCase() === modelData ? 3 : 1; border.color: Theme.lineStrong
                MouseArea { anchors.fill: parent; enabled: !form.draft.controller.busy; onClicked: form.draft.selectedColor = parent.modelData }
            }
        }
        Item { Layout.fillWidth: true }
        ActionButton { objectName: "cancelComment"; compact: true; text: "취소"; hint: "작성 취소 · Esc"; enabled: !form.draft.controller.busy; onClicked: form.draft.close() }
        ActionButton { objectName: "applyComment"; compact: true; primary: true; Layout.rightMargin: Theme.shadowSmall; text: form.draft.mode === "reply" ? "답글 추가" : "적용"; hint: "Ctrl+Enter"; enabled: form.draft.canApply; onClicked: form.draft.apply() }
    }
}
