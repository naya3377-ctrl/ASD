// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Comment list grouped by page. Clicking a card jumps to its place on the page;
// clicking a mark on the page scrolls here to its card. Writing happens inside
// the list: a new note is the top card, an edit or reply opens in its card.
Rectangle {
    id: panel; objectName: "commentsPanel"
    required property var controller
    required property var draft
    property string activeTool: "read"
    property bool allowActions: true
    // The card under the pointer, outlined on the page by Main.qml.
    property var hoveredItem: null
    signal toolRequested(string tool)
    color: Theme.surface
    Rectangle { width: Theme.hairline; height: parent.height; color: Theme.lineStrong; z: 5 }

    readonly property var selected: controller.selectedAnnotation
    readonly property string selectedKey: selected && selected.id ? selected.page + ":" + selected.id : ""
    readonly property bool canMark: allowActions && controller.canAnnotate && !controller.ocrBusy
    readonly property var colors: ["#ffd54f","#8ed7ad","#7dbbe6","#ef9bc0","#bcadff"]

    // With words selected the note goes on them; otherwise pick a place.
    function addNote() {
        if (!settleDraft()) return;
        if (controller.textSelection.count > 0) controller.composeSelectionComment();
        else toolRequested("note");
    }
    function applyMarkup(kind) {
        if (controller.textSelection.count > 0) controller.annotateSelection(kind);
        toolRequested(kind);
    }
    // Leaving a draft by clicking elsewhere keeps work: changed drafts are
    // applied, untouched ones are simply closed.
    function settleDraft() {
        if (!draft.visible) return true;
        if (draft.changed && draft.canApply) { draft.apply(); return false; }
        if (!draft.changed) { draft.close(); return true; }
        return false;
    }
    function choose(item) {
        if (draft.belongsTo(item)) return;
        settleDraft();
        controller.selectAnnotation(item.page, item.id);
    }
    function indexOfSelected() {
        var list = controller.annotations;
        for (var i = 0; i < list.length; ++i)
            if (list[i].id === selected.id && list[i].page === selected.page) return i;
        return -1;
    }
    // Bring the chosen card into view, whichever side the choice came from.
    onSelectedKeyChanged: Qt.callLater(function() { var i = panel.indexOfSelected(); if (i >= 0) comments.positionViewAtIndex(i, ListView.Contain); })
    // A new note is written at the top: show it.
    Connections {
        target: panel.draft
        function onVisibleChanged() { if (panel.draft.visible && panel.draft.mode === "new") Qt.callLater(comments.positionViewAtBeginning); }
    }

    // Header: the title set large over a heavy rule, the count in figures.
    Item {
        id: header; width: parent.width; height: 78
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 22; anchors.rightMargin: 12; anchors.topMargin: 6; spacing: 10
            Text { text: "주석"; font.family: Theme.displayFamily; font.pixelSize: Theme.title+2; font.weight: Font.Bold; color: Theme.ink }
            Text {
                objectName: "commentCount"; Layout.alignment: Qt.AlignBaseline
                text: String(panel.controller.annotations.length).padStart(2, "0")
                font.family: Theme.monoFamily; font.pixelSize: Theme.small; color: Theme.inkMuted
            }
            Item { Layout.fillWidth: true }
            Rectangle {
                visible: panel.controller.annotationsLoading; width: 8; height: 8; color: "transparent"; border.color: Theme.ink; border.width: Theme.border
                RotationAnimation on rotation { running: panel.controller.annotationsLoading; from: 0; to: 90; duration: 400; loops: Animation.Infinite }
            }
            ActionButton { glyph: "close"; compact: true; hint: "주석 목록 닫기"; onClicked: panel.toolRequested("closeComments") }
        }
        Rectangle { x: 22; anchors.bottom: parent.bottom; width: parent.width-22-16; height: Theme.rule; color: Theme.ink }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: 22; anchors.rightMargin: 16; anchors.topMargin: header.height+14; anchors.bottomMargin: 12; spacing: 12
        // Tools and colour for new marks, one row.
        RowLayout {
            id: toolsRow; Layout.fillWidth: true; spacing: 2
            ActionButton { objectName: "commentHighlightButton"; glyph: "highlight"; compact: true; hint: "형광펜 · 글자를 선택하거나 드래그"; active: panel.activeTool==="highlight"; enabled: panel.canMark; onClicked: panel.applyMarkup("highlight") }
            ActionButton { objectName: "commentUnderlineButton"; glyph: "underline"; compact: true; hint: "밑줄"; active: panel.activeTool==="underline"; enabled: panel.canMark; onClicked: panel.applyMarkup("underline") }
            ActionButton { objectName: "commentStrikeoutButton"; glyph: "strikeout"; compact: true; hint: "취소선"; active: panel.activeTool==="strikeout"; enabled: panel.canMark; onClicked: panel.applyMarkup("strikeout") }
            ActionButton { objectName: "commentNoteButton"; glyph: "note"; compact: true; hint: "메모 · 선택한 글자에, 또는 페이지에서 위치 클릭"; active: panel.activeTool==="note"; enabled: panel.canMark; onClicked: panel.addNote() }
            Item { Layout.fillWidth: true }
            // Comment colours are the document's own data: the only colour here.
            Repeater {
                model: panel.colors
                delegate: Item {
                    required property string modelData
                    Layout.preferredWidth: 20; Layout.preferredHeight: 20
                    readonly property bool chosen: panel.controller.annotationColor===modelData
                    Rectangle { anchors.centerIn: parent; width: 18; height: 18; color: "transparent"; border.color: Theme.ink; border.width: Theme.border; visible: parent.chosen }
                    Rectangle { anchors.centerIn: parent; width: 12; height: 12; color: parent.modelData; border.color: Theme.ink; border.width: Theme.hairline }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: panel.controller.setAnnotationColor(parent.modelData) }
                }
            }
            Rectangle { Layout.preferredWidth: Theme.hairline; Layout.preferredHeight: 18; Layout.leftMargin: 6; Layout.rightMargin: 4; color: Theme.lineSoft }
            ActionButton { glyph: "undo"; compact: true; hint: "실행 취소 · Ctrl+Z"; enabled: panel.canMark && panel.controller.document.canUndo; onClicked: panel.controller.undo() }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            Text { text: "작성자"; font.family: Theme.monoFamily; font.pixelSize: Theme.label; font.letterSpacing: Theme.labelSpacing; color: Theme.inkMuted }
            TextField {
                id: authorInput; objectName: "annotationAuthorInput"; Layout.fillWidth: true; text: panel.controller.annotationAuthor
                placeholderText: "이름"; selectByMouse: true; font.pixelSize: Theme.body; color: Theme.ink; implicitHeight: 30
                leftPadding: 2; placeholderTextColor: Theme.inkFaint; selectionColor: Theme.ink; selectedTextColor: Theme.surface
                background: Rectangle {
                    color: "transparent"
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: authorInput.activeFocus ? Theme.borderStrong : Theme.hairline; color: authorInput.activeFocus ? Theme.ink : Theme.lineSoft }
                }
                onEditingFinished: panel.controller.setAnnotationAuthor(text)
            }
        }

        ListView {
            id: comments; objectName: "commentsList"
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.topMargin: 4; clip: true
            model: panel.controller.annotations; spacing: 0
            ScrollBar.vertical: AppScrollBar { }
            // A new note is written at the top of the list.
            header: Loader {
                width: comments.width
                active: panel.draft.visible && panel.draft.mode === "new"
                height: active && item ? item.implicitHeight + 18 : 0
                sourceComponent: Block {
                    width: comments.width-8; implicitHeight: newForm.implicitHeight + 34
                    Rectangle { width: parent.width; height: Theme.borderStrong+1; color: Theme.ink }
                    CommentForm { id: newForm; draft: panel.draft; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 16; anchors.topMargin: 20 }
                }
            }
            delegate: Column {
              id: entry; required property var modelData; required property int index
              width: comments.width-8; spacing: 0
              // Page heading above the first card of each page: figures and a hairline.
              Item {
                  visible: entry.index===0 || panel.controller.annotations[entry.index-1].page!==entry.modelData.page
                  width: entry.width; height: pageLabel.implicitHeight+(entry.index>0 ? 26 : 8)
                  Text {
                      id: pageLabel; anchors.bottom: parent.bottom; anchors.bottomMargin: 6
                      text: "p. " + (entry.modelData.page+1); font.family: Theme.monoFamily; font.pixelSize: Theme.label; font.letterSpacing: Theme.labelSpacing; color: Theme.ink
                  }
                  Rectangle { anchors.left: pageLabel.right; anchors.leftMargin: 10; anchors.right: parent.right; anchors.verticalCenter: pageLabel.verticalCenter; height: Theme.hairline; color: Theme.ink }
              }
              Rectangle {
                id: card; readonly property var modelData: entry.modelData; readonly property int index: entry.index
                objectName: "commentCard"+index
                readonly property bool selected: panel.selected.id===modelData.id && panel.selected.page===modelData.page
                readonly property bool drafting: panel.draft.belongsTo(modelData)
                x: Math.min(modelData.depth,2)*18; width: entry.width-x
                height: cardLayout.implicitHeight+28
                // Selected: framed in ink with a solid rule on the left. Hover: a quiet grey.
                color: cardHover.hovered && !selected ? Theme.hover : Theme.surface
                border.color: selected ? Theme.ink : "transparent"; border.width: Theme.border
                Rectangle { visible: card.selected; width: Theme.rule; height: parent.height; color: Theme.ink }
                Rectangle { visible: !card.selected; anchors.bottom: parent.bottom; width: parent.width; height: Theme.hairline; color: Theme.lineSoft }
                HoverHandler { id: cardHover; onHoveredChanged: panel.hoveredItem = hovered ? card.modelData : (panel.hoveredItem === card.modelData ? null : panel.hoveredItem) }
                TapHandler {
                    enabled: !card.drafting
                    onTapped: panel.choose(card.modelData)
                    onDoubleTapped: { panel.choose(card.modelData); if(card.modelData.editable) panel.controller.editSelectedAnnotation("edit"); }
                }
                ColumnLayout {
                    id: cardLayout; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: card.selected ? 18 : 14; anchors.rightMargin: 14; anchors.topMargin: 14; spacing: 7
                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
                        // The mark's own colour, as a small square.
                        Rectangle { visible: !card.modelData.reply; width: 9; height: 9; color: card.modelData.color || Theme.inkFaint; border.color: Theme.ink; border.width: Theme.hairline }
                        Text { text: card.modelData.reply ? "↳ 답글" : card.modelData.label; font.family: Theme.monoFamily; font.pixelSize: Theme.label-1; font.letterSpacing: Theme.labelSpacing; color: Theme.inkMuted; textFormat: Text.PlainText }
                        Text { text: card.modelData.author || "작성자 없음"; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: Theme.body; font.weight: Font.Bold; color: Theme.ink; textFormat: Text.PlainText }
                        Text {
                            visible: !!card.modelData.created; font.family: Theme.monoFamily; font.pixelSize: Theme.label-1; color: Theme.inkFaint; textFormat: Text.PlainText
                            text: card.modelData.created.slice(0,2)==="D:" ? card.modelData.created.slice(2,6)+"."+card.modelData.created.slice(6,8)+"."+card.modelData.created.slice(8,10) : card.modelData.created
                        }
                    }
                    // The marked words, set off by a rule like a quotation.
                    RowLayout {
                        visible: !!card.modelData.quote && !card.modelData.reply; Layout.fillWidth: true; spacing: 10
                        Rectangle { Layout.fillHeight: true; Layout.preferredWidth: Theme.borderStrong; color: Theme.ink }
                        Text {
                            Layout.fillWidth: true
                            text: card.modelData.quote.replace(/\s+/g," "); wrapMode: Text.Wrap
                            maximumLineCount: card.selected ? 4 : 2; elide: Text.ElideRight
                            font.pixelSize: Theme.small; lineHeight: 1.2; color: Theme.inkMuted; textFormat: Text.PlainText
                        }
                    }
                    Text {
                        visible: !card.drafting || panel.draft.mode === "reply"; Layout.fillWidth: true
                        text: card.modelData.content || (card.modelData.state ? "검토 상태: "+card.modelData.state : card.modelData.quote ? "" : "내용 없는 주석")
                        wrapMode: Text.Wrap; maximumLineCount: card.selected ? 8 : 3; elide: Text.ElideRight
                        font.pixelSize: Theme.lead-1; lineHeight: 1.3; color: card.modelData.content ? Theme.ink : Theme.inkFaint; textFormat: Text.PlainText
                    }
                    Text { visible: !card.modelData.editable && card.selected; Layout.fillWidth: true; text: "읽기 전용 · 원본 주석 보존"; font.family: Theme.monoFamily; font.pixelSize: Theme.label-1; color: Theme.inkFaint }
                    RowLayout {
                        visible: card.selected && card.modelData.editable && !card.drafting; spacing: 6; Layout.topMargin: 4
                        ActionButton { objectName: "editComment"+card.index; compact: true; outlined: true; text: "수정"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: { panel.settleDraft(); panel.controller.editSelectedAnnotation("edit"); } }
                        ActionButton { objectName: "replyComment"+card.index; compact: true; outlined: true; text: "답글"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: { panel.settleDraft(); panel.controller.editSelectedAnnotation("reply"); } }
                        Item { Layout.fillWidth: true }
                        ActionButton { glyph: "delete"; compact: true; hint: "주석과 답글 삭제"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: panel.controller.deleteSelectedAnnotation() }
                    }
                    Loader {
                        Layout.fillWidth: true; active: card.drafting; visible: active; Layout.topMargin: 6
                        sourceComponent: CommentForm { draft: panel.draft }
                    }
                }
              }
            }
            Column {
                visible: !comments.count && !panel.controller.annotationsLoading && !panel.draft.visible
                anchors.centerIn: parent; width: parent.width-24; spacing: 14
                BrandMark { anchors.horizontalCenter: parent.horizontalCenter; size: 40 }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: "아직 주석이 없어요"; font.family: Theme.displayFamily; font.pixelSize: Theme.lead+3; font.weight: Font.Bold; color: Theme.ink }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; text: "글자를 드래그한 뒤 형광펜이나 메모를 누르세요. 선택 없이 메모를 누르면 페이지에서 자리를 고를 수 있어요."; font.pixelSize: Theme.small; lineHeight: 1.4; color: Theme.inkMuted }
            }
        }
        Rectangle { Layout.fillWidth: true; height: Theme.hairline; color: Theme.lineSoft }
        Text { Layout.fillWidth: true; text: "카드를 누르면 그 위치로 이동해요 · 주석은 저장하면 PDF에 함께 남아요"; wrapMode: Text.WordWrap; font.pixelSize: Theme.label; lineHeight: 1.3; color: Theme.inkMuted }
    }
}
