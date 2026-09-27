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
    Rectangle { width: Theme.border; height: parent.height; color: Theme.lineStrong; z: 5 }

    readonly property var selected: controller.selectedAnnotation
    readonly property string selectedKey: selected && selected.id ? selected.page + ":" + selected.id : ""
    readonly property bool canMark: allowActions && controller.canAnnotate && !controller.ocrBusy
    readonly property var colors: ["#ffd54f","#8ed7ad","#7dbbe6","#ef9bc0","#bcadff"]

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

    // Header: the comment mode's yellow block, with the count in a black circle.
    Rectangle {
        id: header; width: parent.width; height: 64; color: Theme.yellow
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: Theme.border; color: Theme.black }
        Geo { kind: "circle"; size: 92; color: "#26ffffff"; x: parent.width-128; y: -30 }
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 10; anchors.bottomMargin: Theme.border; spacing: 10
            Text { text: "주석"; font.pixelSize: 24; font.weight: Font.Black; font.letterSpacing: -.5; color: Theme.black }
            Rectangle {
                color: Theme.black; implicitWidth: Math.max(26, countText.implicitWidth + 12); implicitHeight: 26; radius: 13
                Text { id: countText; anchors.centerIn: parent; text: panel.controller.annotations.length; font.pixelSize: 12; font.weight: Font.Bold; color: Theme.white }
            }
            Item { Layout.fillWidth: true }
            Geo {
                visible: panel.controller.annotationsLoading; kind: "square"; size: 10; color: Theme.black
                RotationAnimation on rotation { running: panel.controller.annotationsLoading; from: 0; to: 90; duration: 420; loops: Animation.Infinite }
            }
            ActionButton { glyph: "close"; compact: true; onLight: true; hint: "주석 목록 닫기"; onClicked: panel.toolRequested("closeComments") }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 12; anchors.topMargin: header.height+14; anchors.bottomMargin: 10; spacing: 12
        // Tools and colour for new marks, one compact row.
        Block {
            Layout.fillWidth: true; implicitHeight: toolsRow.implicitHeight + 12; Layout.rightMargin: Theme.shadowSmall
            fill: Theme.raised; shadow: Theme.shadowSmall
            RowLayout {
                id: toolsRow; anchors.fill: parent; anchors.margins: 6; spacing: 2
                ActionButton { objectName: "commentHighlightButton"; glyph: "highlight"; compact: true; hint: "형광펜 · 글자를 선택하거나 드래그"; active: panel.activeTool==="highlight"; enabled: panel.canMark; onClicked: panel.applyMarkup("highlight") }
                ActionButton { objectName: "commentUnderlineButton"; glyph: "underline"; compact: true; hint: "밑줄"; active: panel.activeTool==="underline"; enabled: panel.canMark; onClicked: panel.applyMarkup("underline") }
                ActionButton { objectName: "commentStrikeoutButton"; glyph: "strikeout"; compact: true; hint: "취소선"; active: panel.activeTool==="strikeout"; enabled: panel.canMark; onClicked: panel.applyMarkup("strikeout") }
                ActionButton { objectName: "commentNoteButton"; glyph: "note"; compact: true; hint: "메모 · 페이지에서 위치 클릭"; active: panel.activeTool==="note"; enabled: panel.canMark; onClicked: panel.toolRequested("note") }
                Item { Layout.fillWidth: true }
                Repeater {
                    model: panel.colors
                    delegate: Rectangle {
                        required property string modelData
                        Layout.preferredWidth: 16; Layout.preferredHeight: 16; radius: 8; color: modelData
                        border.width: panel.controller.annotationColor===modelData ? 3 : 1; border.color: Theme.lineStrong
                        MouseArea { anchors.fill: parent; anchors.margins: -3; onClicked: panel.controller.setAnnotationColor(parent.modelData) }
                    }
                }
                ActionButton { glyph: "undo"; compact: true; hint: "실행 취소 · Ctrl+Z"; enabled: panel.canMark && panel.controller.document.canUndo; onClicked: panel.controller.undo() }
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 6
            Text { text: "작성자"; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1; color: Theme.ink }
            TextField {
                objectName: "annotationAuthorInput"; Layout.fillWidth: true; text: panel.controller.annotationAuthor
                placeholderText: "이름"; selectByMouse: true; font.pixelSize: 12; color: Theme.ink; implicitHeight: 28
                background: Rectangle { color: Theme.field; border.width: Theme.border; border.color: parent.activeFocus ? Theme.focusRing : Theme.lineStrong }
                onEditingFinished: panel.controller.setAnnotationAuthor(text)
            }
        }

        ListView {
            id: comments; objectName: "commentsList"
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            model: panel.controller.annotations; spacing: 12
            ScrollBar.vertical: BauhausScrollBar { }
            // A new note is written at the top of the list.
            header: Loader {
                width: comments.width
                active: panel.draft.visible && panel.draft.mode === "new"
                height: active && item ? item.implicitHeight + 16 : 0
                sourceComponent: Block {
                    width: comments.width-Theme.shadowLarge-2; implicitHeight: newForm.implicitHeight + 30
                    fill: Theme.raised; shadow: Theme.shadowLarge; outlineWidth: Theme.border
                    Rectangle { width: parent.width; height: 6; color: Theme.red }
                    CommentForm { id: newForm; draft: panel.draft; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14; anchors.topMargin: 18 }
                }
            }
            delegate: Column {
              id: entry; required property var modelData; required property int index
              width: comments.width; spacing: 4
              // Page heading above the first card of each page: a black label block.
              Item {
                  visible: entry.index===0 || panel.controller.annotations[entry.index-1].page!==entry.modelData.page
                  width: pageLabel.implicitWidth+16; height: pageLabel.implicitHeight+8+(entry.index>0 ? 10 : 0)
                  Rectangle {
                      anchors.bottom: parent.bottom; width: parent.width; height: pageLabel.implicitHeight+8; color: Theme.lineStrong
                      Text { id: pageLabel; anchors.centerIn: parent; text: (entry.modelData.page+1)+"쪽"; font.pixelSize: 11; font.weight: Font.Black; font.letterSpacing: .6; color: Theme.dark ? Theme.black : Theme.white }
                  }
              }
              Block {
                id: card; readonly property var modelData: entry.modelData; readonly property int index: entry.index
                objectName: "commentCard"+index
                readonly property bool selected: panel.selected.id===modelData.id && panel.selected.page===modelData.page
                readonly property bool drafting: panel.draft.belongsTo(modelData)
                x: Math.min(modelData.depth,2)*16; width: comments.width-x-Theme.shadowLarge-2
                height: cardLayout.implicitHeight+22
                // Selected: pale yellow and raised on a deeper shadow. Hover: a small lift.
                fill: selected ? Theme.paleYellow : Theme.raised
                shadow: selected ? Theme.shadowLarge : Theme.shadowSmall
                lifted: cardHover.hovered && !selected
                HoverHandler { id: cardHover; onHoveredChanged: panel.hoveredItem = hovered ? card.modelData : (panel.hoveredItem === card.modelData ? null : panel.hoveredItem) }
                // The mark's own colour as a solid band down the left edge.
                Rectangle {
                    parent: card.face; x: Theme.border; y: Theme.border; width: 6; height: card.height-2*Theme.border
                    color: card.modelData.color || Theme.inkFaint; visible: !card.modelData.reply
                    Rectangle { anchors.right: parent.right; width: Theme.border; height: parent.height; color: Theme.lineStrong }
                }
                // Corner form by kind: note = circle, highlight = square, lines = triangle.
                Geo {
                    parent: card.face; x: card.width-size-8; y: 8; size: 9
                    kind: card.modelData.type==="Text" ? "circle" : card.modelData.type==="Highlight" ? "square" : "triangle"
                    color: Theme.primary(card.index)
                }
                TapHandler {
                    enabled: !card.drafting
                    onTapped: panel.choose(card.modelData)
                    onDoubleTapped: { panel.choose(card.modelData); if(card.modelData.editable) panel.controller.editSelectedAnnotation("edit"); }
                }
                ColumnLayout {
                    id: cardLayout; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: 20; anchors.rightMargin: 22; anchors.topMargin: 11; spacing: 6
                    RowLayout {
                        Layout.fillWidth: true; spacing: 6
                        Text { text: card.modelData.reply ? "↳ 답글" : card.modelData.label; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1; color: Theme.inkMuted; textFormat: Text.PlainText }
                        Text { text: card.modelData.author || "작성자 없음"; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: 12; font.weight: Font.Black; color: Theme.ink; textFormat: Text.PlainText }
                        Text {
                            visible: !!card.modelData.created; font.pixelSize: 10; color: Theme.inkFaint; textFormat: Text.PlainText
                            text: card.modelData.created.slice(0,2)==="D:" ? card.modelData.created.slice(2,6)+"."+card.modelData.created.slice(6,8)+"."+card.modelData.created.slice(8,10) : card.modelData.created
                        }
                    }
                    // The marked words, so the card says what it is about.
                    Text {
                        visible: !!card.modelData.quote && !card.modelData.reply; Layout.fillWidth: true
                        text: "“" + card.modelData.quote.replace(/\s+/g," ") + "”"; wrapMode: Text.Wrap
                        maximumLineCount: card.selected ? 4 : 2; elide: Text.ElideRight
                        font.pixelSize: 11; color: Theme.inkMuted; textFormat: Text.PlainText
                    }
                    Text {
                        visible: !card.drafting || panel.draft.mode === "reply"; Layout.fillWidth: true
                        text: card.modelData.content || (card.modelData.state ? "검토 상태: "+card.modelData.state : card.modelData.quote ? "" : "내용 없는 주석")
                        wrapMode: Text.Wrap; maximumLineCount: card.selected ? 8 : 3; elide: Text.ElideRight
                        font.pixelSize: 13; font.weight: Font.Medium; lineHeight: 1.15; color: Theme.ink; textFormat: Text.PlainText
                    }
                    Text { visible: !card.modelData.editable && card.selected; Layout.fillWidth: true; text: "읽기 전용 · 원본 주석 보존"; font.pixelSize: 10; color: Theme.inkFaint }
                    RowLayout {
                        visible: card.selected && card.modelData.editable && !card.drafting; spacing: 2; Layout.topMargin: 2
                        ActionButton { objectName: "editComment"+card.index; compact: true; outlined: true; text: "수정"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: { panel.settleDraft(); panel.controller.editSelectedAnnotation("edit"); } }
                        ActionButton { objectName: "replyComment"+card.index; compact: true; outlined: true; Layout.leftMargin: 6; text: "답글"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: { panel.settleDraft(); panel.controller.editSelectedAnnotation("reply"); } }
                        Item { Layout.fillWidth: true }
                        ActionButton { glyph: "delete"; compact: true; hint: "주석과 답글 삭제"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: panel.controller.deleteSelectedAnnotation() }
                    }
                    Loader {
                        Layout.fillWidth: true; active: card.drafting; visible: active; Layout.topMargin: 4
                        sourceComponent: CommentForm { draft: panel.draft }
                    }
                }
              }
            }
            Column {
                visible: !comments.count && !panel.controller.annotationsLoading && !panel.draft.visible
                anchors.centerIn: parent; width: parent.width-24; spacing: 10
                Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: 8; Geo { kind: "circle"; size: 26; color: Theme.red } Geo { kind: "square"; size: 26; color: Theme.blue; rotation: 45 } Geo { kind: "triangle"; size: 26; color: Theme.yellow } }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: "아직 주석이 없어요"; font.pixelSize: 15; font.weight: Font.Black; color: Theme.ink }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; text: "글자를 선택하고 형광펜을 누르거나, 메모 도구로 페이지를 클릭해 보세요."; font.pixelSize: 12; lineHeight: 1.3; color: Theme.inkMuted }
            }
        }
        Text { Layout.fillWidth: true; text: "카드를 누르면 그 위치로 이동해요 · 주석은 저장하면 PDF에 함께 남아요"; wrapMode: Text.WordWrap; font.pixelSize: 11; color: Theme.inkMuted }
    }
}
