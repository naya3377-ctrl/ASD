// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Writing area for a comment draft, shown in place inside the comment list.
ColumnLayout {
    id: form
    required property var draft
    readonly property var colors: ["#ffd54f","#8ed7ad","#7dbbe6","#ef9bc0","#bcadff"]
    spacing: Theme.gapS
    Component.onCompleted: { body.text = draft.text; author.text = draft.author; body.forceActiveFocus(); }

    Text {
        text: form.draft.mode === "reply" ? "답글 작성" : form.draft.mode === "edit" ? "메모 수정"
            : (form.draft.targetData.kind ? "선택한 글자에 메모 · " : "새 메모 · ") + (Number(form.draft.targetData.page || 0) + 1) + "쪽"
        font.pixelSize: Theme.small; font.weight: Font.DemiBold; color: Theme.ink
    }
    // The words this note will mark.
    RowLayout {
        visible: !!form.draft.targetData.quote; Layout.fillWidth: true; spacing: 9
        Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 2; radius: 1; color: Theme.lineStrong }
        Text {
            Layout.fillWidth: true
            text: String(form.draft.targetData.quote || "").replace(/\s+/g, " ")
            wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
            font.pixelSize: Theme.small; color: Theme.inkSoft; textFormat: Text.PlainText
        }
    }
    TextField {
        id: author; objectName: "commentAuthor"; Layout.fillWidth: true
        placeholderText: "작성자"; selectByMouse: true; font.pixelSize: Theme.small; color: Theme.ink; leftPadding: 10; implicitHeight: Theme.control
        placeholderTextColor: Theme.inkFaint; selectionColor: Theme.selection; selectedTextColor: Theme.ink
        enabled: !form.draft.controller.busy
        background: Rectangle { radius: Theme.radius; color: Theme.field; border.width: author.activeFocus ? 2 : Theme.hairline; border.color: author.activeFocus ? Theme.focusRing : Theme.line }
        onTextChanged: form.draft.author = text
    }
    ScrollView {
        Layout.fillWidth: true; Layout.preferredHeight: Math.min(180, Math.max(84, body.implicitHeight + 12))
        TextArea {
            id: body; objectName: "commentBody"
            placeholderText: form.draft.mode === "reply" ? "답글을 입력하세요" : "메모를 입력하세요"
            wrapMode: TextEdit.Wrap; textFormat: TextEdit.PlainText; selectByMouse: true
            font.pixelSize: Theme.body; color: Theme.ink; enabled: !form.draft.controller.busy
            placeholderTextColor: Theme.inkFaint; selectionColor: Theme.selection; selectedTextColor: Theme.ink
            padding: 10
            background: Rectangle { radius: Theme.radius; color: Theme.field; border.width: body.activeFocus ? 2 : Theme.hairline; border.color: body.activeFocus ? Theme.focusRing : Theme.line }
            onTextChanged: form.draft.text = text
            Keys.onPressed: function(event) {
                if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && (event.modifiers & Qt.ControlModifier)) { form.draft.apply(); event.accepted = true; }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 0
        Repeater {
            model: form.draft.mode === "reply" ? [] : form.colors
            delegate: Item {
                required property string modelData
                width: 24; height: 32
                readonly property bool chosen: form.draft.selectedColor.toLowerCase() === modelData
                Rectangle { anchors.centerIn: parent; width: 20; height: 20; radius: 10; color: "transparent"; border.color: Theme.accent; border.width: 2; visible: parent.chosen }
                Rectangle { anchors.centerIn: parent; width: 14; height: 14; radius: 7; color: parent.modelData; border.color: "#2629313a"; border.width: Theme.hairline }
                MouseArea { anchors.fill: parent; enabled: !form.draft.controller.busy; cursorShape: Qt.PointingHandCursor; onClicked: form.draft.selectedColor = parent.modelData }
            }
        }
        Item { Layout.fillWidth: true }
        ActionButton { objectName: "cancelComment"; Layout.rightMargin: Theme.gapXs; compact: true; outlined: true; text: "취소"; hint: "작성 취소 · Esc"; enabled: !form.draft.controller.busy; onClicked: form.draft.close() }
        ActionButton { objectName: "applyComment"; compact: true; primary: true; text: form.draft.mode === "reply" ? "답글 추가" : "적용"; hint: "Ctrl+Enter"; enabled: form.draft.canApply; onClicked: form.draft.apply() }
    }
}
