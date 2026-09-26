// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: panel; objectName: "commentsPanel"
    required property var controller
    property string activeTool: "read"
    property bool allowActions: true
    signal toolRequested(string tool)
    color: Theme.surface
    Rectangle { width: 1; height: parent.height; color: Theme.line }
    function applyMarkup(kind) {
        if(controller.textSelection.count>0) { controller.annotateSelection(kind); toolRequested(kind); }
        else toolRequested(kind);
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 15; spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Text { text: "주석"; font.pixelSize: 19; font.weight: Font.DemiBold; color: Theme.ink }
            Text { text: panel.controller.annotations.length; font.pixelSize: 12; color: Theme.inkMuted }
            Item { Layout.fillWidth: true }
            BusyIndicator { running: panel.controller.annotationsLoading; visible: running; Layout.preferredWidth: 22; Layout.preferredHeight: 22 }
            ActionButton { glyph: "close"; implicitWidth: 28; hint: "읽기로 돌아가기"; enabled: panel.allowActions; onClicked: panel.toolRequested("closeComments") }
        }
        TextField {
            objectName: "annotationAuthorInput"; Layout.fillWidth: true; text: panel.controller.annotationAuthor
            placeholderText: "주석 작성자"; selectByMouse: true; font.pixelSize: 13
            onEditingFinished: panel.controller.setAnnotationAuthor(text)
            color: Theme.ink
            background: Rectangle { radius: Theme.radiusSmall; color: Theme.field; border.color: Theme.lineStrong }
        }
        RowLayout {
            spacing: 4
            ActionButton { objectName: "commentHighlightButton"; glyph: "highlight"; hint: "형광펜 · 글자를 선택하거나 드래그"; active: panel.activeTool==="highlight"; enabled: panel.allowActions && panel.controller.canAnnotate && !panel.controller.ocrBusy; onClicked: panel.applyMarkup("highlight") }
            ActionButton { objectName: "commentUnderlineButton"; glyph: "underline"; hint: "밑줄"; active: panel.activeTool==="underline"; enabled: panel.allowActions && panel.controller.canAnnotate && !panel.controller.ocrBusy; onClicked: panel.applyMarkup("underline") }
            ActionButton { objectName: "commentStrikeoutButton"; glyph: "strikeout"; hint: "취소선"; active: panel.activeTool==="strikeout"; enabled: panel.allowActions && panel.controller.canAnnotate && !panel.controller.ocrBusy; onClicked: panel.applyMarkup("strikeout") }
            ActionButton { objectName: "commentNoteButton"; glyph: "note"; hint: "각주(메모) · 페이지에서 위치 클릭"; active: panel.activeTool==="note"; enabled: panel.allowActions && panel.controller.canAnnotate && !panel.controller.ocrBusy; onClicked: panel.toolRequested("note") }
            Item { Layout.fillWidth: true }
            ActionButton { glyph: "undo"; hint: "실행 취소 · Ctrl+Z"; enabled: panel.allowActions && panel.controller.canAnnotate && panel.controller.document.canUndo; onClicked: panel.controller.undo() }
        }
        RowLayout {
            spacing: 12; Layout.bottomMargin: 2
            Repeater {
                model: ["#ffd54f","#8ed7ad","#7dbbe6","#ef9bc0","#bcadff"]
                delegate: Rectangle {
                    required property string modelData
                    width: 23; height: 23; radius: 12; color: modelData
                    border.width: panel.controller.annotationColor===modelData ? 2 : 0; border.color: Theme.ink
                    MouseArea { anchors.fill: parent; onClicked: panel.controller.setAnnotationColor(parent.modelData) }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
        ListView {
            id: comments; objectName: "commentsList"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            model: panel.controller.annotations; spacing: 8
            ScrollBar.vertical: ScrollBar { }
            delegate: Rectangle {
                id: card; required property var modelData; required property int index
                objectName: "commentCard"+index
                property bool selected: panel.controller.selectedAnnotation.id===modelData.id && panel.controller.selectedAnnotation.page===modelData.page
                x: Math.min(modelData.depth,2)*12; width: comments.width-x-7
                height: cardLayout.implicitHeight+24; radius: 9
                color: selected ? Theme.accentSoft : Theme.raised; border.color: selected ? Theme.accent : Theme.line
                MouseArea { anchors.fill: parent; enabled: panel.allowActions; onClicked: panel.controller.selectAnnotation(card.modelData.page,card.modelData.id); onDoubleClicked: { panel.controller.selectAnnotation(card.modelData.page,card.modelData.id); panel.controller.editSelectedAnnotation("edit"); } }
                ColumnLayout {
                    id: cardLayout; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 12; spacing: 7
                    RowLayout {
                        spacing: 7; Layout.fillWidth: true
                        Rectangle { width: 7; height: 7; radius: 4; color: card.modelData.color }
                        Text { text: card.modelData.reply ? "답글" : card.modelData.label; color: Theme.inkSoft; font.pixelSize: 11; textFormat: Text.PlainText }
                        Item { Layout.fillWidth: true }
                        Text { text: (card.modelData.page+1)+"쪽"; font.pixelSize: 11; color: Theme.inkMuted }
                    }
                    Text { Layout.fillWidth: true; text: card.modelData.author || "작성자 없음"; elide: Text.ElideRight; font.pixelSize: 13; font.weight: Font.DemiBold; color: Theme.ink; textFormat: Text.PlainText }
                    Text { Layout.fillWidth: true; text: card.modelData.content || card.modelData.quote || (card.modelData.state ? "검토 상태: "+card.modelData.state : "내용 없는 주석"); wrapMode: Text.Wrap; maximumLineCount: card.selected ? 20 : 4; elide: Text.ElideRight; font.pixelSize: 13; color: Theme.inkSoft; textFormat: Text.PlainText }
                    Text { visible: !card.modelData.editable; Layout.fillWidth: true; text: "읽기 전용 · 원본 주석 보존"; font.pixelSize: 10; color: Theme.inkMuted }
                    Text { visible: !!card.modelData.created; text: card.modelData.created.slice(0,2)==="D:" ? card.modelData.created.slice(2,6)+"."+card.modelData.created.slice(6,8)+"."+card.modelData.created.slice(8,10) : card.modelData.created; font.pixelSize: 10; color: Theme.inkMuted; textFormat: Text.PlainText }
                    RowLayout {
                        visible: card.selected && card.modelData.editable; spacing: 2
                        ActionButton { objectName: "editComment"+card.index; text: "수정"; implicitHeight: 29; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: panel.controller.editSelectedAnnotation("edit") }
                        ActionButton { objectName: "replyComment"+card.index; text: "답글"; implicitHeight: 29; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: panel.controller.editSelectedAnnotation("reply") }
                        Item { Layout.fillWidth: true }
                        ActionButton { glyph: "delete"; implicitHeight: 29; hint: "주석과 답글 삭제"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: panel.controller.deleteSelectedAnnotation() }
                    }
                }
            }
            Text { visible: !panel.controller.annotations.length && !panel.controller.annotationsLoading; anchors.centerIn: parent; width: parent.width-20; text: "아직 주석이 없어요.\n글자를 선택하거나 메모를 남겨 보세요."; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; font.pixelSize: 12; lineHeight: 1.5; color: Theme.inkMuted }
        }
        Text { Layout.fillWidth: true; text: "주석과 답글은 PDF에 함께 저장돼요."; wrapMode: Text.WordWrap; font.pixelSize: 11; color: Theme.inkMuted }
    }
}
