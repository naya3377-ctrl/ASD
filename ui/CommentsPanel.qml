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
    Rectangle { width: Theme.hairline; height: parent.height; color: Theme.lineSoft; z: 5 }

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

    // Header: a quiet title with the count in a pill.
    Item {
        id: header; width: parent.width; height: 56
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 10; spacing: 8
            Text { text: "주석"; font.pixelSize: Theme.title3; font.weight: Font.Bold; color: Theme.ink }
            Rectangle {
                objectName: "commentCount"; radius: height/2; color: Theme.accentSoft
                implicitWidth: Math.max(22, countText.implicitWidth+14); implicitHeight: 20
                Text { id: countText; anchors.centerIn: parent; text: panel.controller.annotations.length; font.pixelSize: Theme.caption; font.weight: Font.Bold; font.features: ({ "tnum": 1 }); color: Theme.accentInk }
            }
            Item { Layout.fillWidth: true }
            BusyIndicator { running: panel.controller.annotationsLoading; visible: running; implicitWidth: 18; implicitHeight: 18 }
            ActionButton { glyph: "close"; compact: true; hint: "주석 목록 닫기"; onClicked: panel.toolRequested("closeComments") }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 12; anchors.topMargin: header.height; anchors.bottomMargin: 12; spacing: 10
        // Tools and colour for new marks.
        RowLayout {
            id: toolsRow; Layout.fillWidth: true; spacing: 8
            Rectangle {
                radius: Theme.radius+1; color: Theme.well
                implicitWidth: toolButtons.implicitWidth+4; implicitHeight: toolButtons.implicitHeight+4
                Row {
                    id: toolButtons; x: 2; y: 2; spacing: 1
                    ActionButton { objectName: "commentHighlightButton"; glyph: "highlight"; compact: true; hint: "형광펜 · 글자를 선택하거나 드래그"; active: panel.activeTool==="highlight"; enabled: panel.canMark; onClicked: panel.applyMarkup("highlight") }
                    ActionButton { objectName: "commentUnderlineButton"; glyph: "underline"; compact: true; hint: "밑줄"; active: panel.activeTool==="underline"; enabled: panel.canMark; onClicked: panel.applyMarkup("underline") }
                    ActionButton { objectName: "commentStrikeoutButton"; glyph: "strikeout"; compact: true; hint: "취소선"; active: panel.activeTool==="strikeout"; enabled: panel.canMark; onClicked: panel.applyMarkup("strikeout") }
                    ActionButton { objectName: "commentNoteButton"; glyph: "note"; compact: true; hint: "메모 · 선택한 글자에, 또는 페이지에서 위치 클릭"; active: panel.activeTool==="note"; enabled: panel.canMark; onClicked: panel.addNote() }
                }
            }
            Item { Layout.fillWidth: true }
            // Colour wells for new marks: these are the colours saved in the PDF.
            Row {
                spacing: 5
                Repeater {
                    model: panel.colors
                    delegate: Item {
                        required property string modelData
                        width: 20; height: 20
                        readonly property bool chosen: panel.controller.annotationColor===modelData
                        Rectangle { anchors.centerIn: parent; width: 20; height: 20; radius: 10; color: "transparent"; border.color: Theme.accent; border.width: 2; visible: parent.chosen }
                        Rectangle { anchors.centerIn: parent; width: 14; height: 14; radius: 7; color: parent.modelData; border.color: "#262a2420"; border.width: Theme.hairline }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: panel.controller.setAnnotationColor(parent.modelData) }
                    }
                }
            }
            ActionButton { glyph: "undo"; compact: true; hint: "실행 취소 · Ctrl+Z"; enabled: panel.canMark && panel.controller.document.canUndo; onClicked: panel.controller.undo() }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Text { text: "작성자"; font.pixelSize: Theme.small; font.weight: Font.DemiBold; color: Theme.inkMuted }
            TextField {
                id: authorInput; objectName: "annotationAuthorInput"; Layout.fillWidth: true; text: panel.controller.annotationAuthor
                placeholderText: "이름"; selectByMouse: true; font.pixelSize: Theme.body; color: Theme.ink; implicitHeight: 28
                leftPadding: 9; placeholderTextColor: Theme.inkFaint; selectionColor: Theme.selection; selectedTextColor: Theme.ink
                background: Rectangle {
                    radius: Theme.radius; color: Theme.field; border.width: authorInput.activeFocus ? 2 : Theme.hairline
                    border.color: authorInput.activeFocus ? Theme.focusRing : Theme.line
                }
                onEditingFinished: panel.controller.setAnnotationAuthor(text)
            }
        }

        ListView {
            id: comments; objectName: "commentsList"
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.topMargin: 2; clip: true
            model: panel.controller.annotations; spacing: 8
            topMargin: 4; bottomMargin: 10; leftMargin: 2; rightMargin: 2
            ScrollBar.vertical: AppScrollBar { }
            // A new note is written at the top of the list.
            header: Loader {
                width: comments.width-4
                active: panel.draft.visible && panel.draft.mode === "new"
                height: active && item ? item.implicitHeight : 0
                sourceComponent: Item {
                    implicitHeight: newForm.implicitHeight + 28 + 14   // the card, then a gap before the list
                    Block {
                        width: parent.width; height: parent.height - 14
                        shadow: "medium"; outline: Theme.accent; outlineWidth: 1.5
                        CommentForm { id: newForm; draft: panel.draft; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14 }
                    }
                }
            }
            delegate: Column {
              id: entry; required property var modelData; required property int index
              width: comments.width-4; spacing: 0
              // Page heading above the first card of each page.
              Item {
                  visible: entry.index===0 || panel.controller.annotations[entry.index-1].page!==entry.modelData.page
                  width: entry.width; height: pageLabel.implicitHeight+(entry.index>0 ? 16 : 4)
                  Text {
                      id: pageLabel; anchors.bottom: parent.bottom; anchors.bottomMargin: 6; x: 4
                      text: (entry.modelData.page+1) + "쪽"; font.pixelSize: Theme.small; font.weight: Font.DemiBold; color: Theme.inkMuted
                  }
              }
              Item {
                id: card; readonly property var modelData: entry.modelData; readonly property int index: entry.index
                objectName: "commentCard"+index
                readonly property bool selected: panel.selected.id===modelData.id && panel.selected.page===modelData.page
                readonly property bool drafting: panel.draft.belongsTo(modelData)
                x: Math.min(modelData.depth,2)*16; width: entry.width-x
                height: cardLayout.implicitHeight+26
                // Replies hang from a thin thread on the left.
                Rectangle { visible: !!card.modelData.reply; x: -9; y: -6; width: 2; height: 22; radius: 1; color: Theme.line }
                Block {
                    anchors.fill: parent; shadow: card.selected ? "medium" : "small"
                    fill: cardHover.hovered && !card.selected ? Qt.darker(Theme.raised, Theme.dark ? .92 : 1.012) : Theme.raised
                    outline: card.selected ? Theme.accent : Theme.lineSoft; outlineWidth: card.selected ? 1.5 : Theme.hairline
                }
                HoverHandler { id: cardHover; onHoveredChanged: panel.hoveredItem = hovered ? card.modelData : (panel.hoveredItem === card.modelData ? null : panel.hoveredItem) }
                TapHandler {
                    enabled: !card.drafting
                    onTapped: panel.choose(card.modelData)
                    onDoubleTapped: { panel.choose(card.modelData); if(card.modelData.editable) panel.controller.editSelectedAnnotation("edit"); }
                }
                ColumnLayout {
                    id: cardLayout; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: 14; anchors.rightMargin: 12; anchors.topMargin: 12; spacing: 6
                    RowLayout {
                        Layout.fillWidth: true; spacing: 7
                        // The mark's own colour, as a small dot.
                        Rectangle { visible: !card.modelData.reply; width: 9; height: 9; radius: 4.5; color: card.modelData.color || Theme.inkFaint; border.color: "#332a2420"; border.width: Theme.hairline }
                        Text { text: card.modelData.author || "작성자 없음"; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: Theme.body; font.weight: Font.DemiBold; color: Theme.ink; textFormat: Text.PlainText }
                        Text {
                            visible: !!card.modelData.created; font.pixelSize: Theme.caption; font.features: ({ "tnum": 1 }); color: Theme.inkFaint; textFormat: Text.PlainText
                            text: card.modelData.created.slice(0,2)==="D:" ? card.modelData.created.slice(2,6)+"."+card.modelData.created.slice(6,8)+"."+card.modelData.created.slice(8,10) : card.modelData.created
                        }
                    }
                    Text { text: card.modelData.reply ? "답글" : card.modelData.label; font.pixelSize: Theme.caption; color: Theme.inkMuted; textFormat: Text.PlainText; Layout.topMargin: -3 }
                    // The marked words, set off by a leather-brown rule like a quotation.
                    RowLayout {
                        visible: !!card.modelData.quote && !card.modelData.reply; Layout.fillWidth: true; spacing: 9
                        Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 3; radius: 1.5; color: Theme.leather; opacity: .75 }
                        Text {
                            Layout.fillWidth: true
                            text: card.modelData.quote.replace(/\s+/g," "); wrapMode: Text.Wrap
                            maximumLineCount: card.selected ? 4 : 2; elide: Text.ElideRight
                            font.pixelSize: Theme.small; lineHeight: 1.25; color: Theme.inkSoft; textFormat: Text.PlainText
                        }
                    }
                    Text {
                        visible: !card.drafting || panel.draft.mode === "reply"; Layout.fillWidth: true
                        text: card.modelData.content || (card.modelData.state ? "검토 상태: "+card.modelData.state : card.modelData.quote ? "" : "내용 없는 주석")
                        wrapMode: Text.Wrap; maximumLineCount: card.selected ? 8 : 3; elide: Text.ElideRight
                        font.pixelSize: Theme.callout; lineHeight: 1.3; color: card.modelData.content ? Theme.ink : Theme.inkFaint; textFormat: Text.PlainText
                    }
                    Text { visible: !card.modelData.editable && card.selected; Layout.fillWidth: true; text: "읽기 전용 · 원본 주석 보존"; font.pixelSize: Theme.caption; color: Theme.inkFaint }
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
            // Nothing yet: the character waits for the first note.
            Column {
                visible: !comments.count && !panel.controller.annotationsLoading && !panel.draft.visible
                anchors.centerIn: parent; width: parent.width-28; spacing: 10
                Image { objectName: "commentsEmptyCharacter"; anchors.horizontalCenter: parent.horizontalCenter; source: "../assets/character/face.png"; width: 118; height: width*sourceSize.height/Math.max(1,sourceSize.width); smooth: true; mipmap: true }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: "아직 주석이 없어요"; font.pixelSize: Theme.headline; font.weight: Font.Bold; color: Theme.ink }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; text: "글자를 드래그한 뒤 형광펜이나 메모를 눌러 보세요. 선택 없이 메모를 누르면 페이지에서 자리를 고를 수 있어요."; font.pixelSize: Theme.small; lineHeight: 1.35; color: Theme.inkMuted }
            }
        }
        Text { Layout.fillWidth: true; text: "카드를 누르면 그 위치로 이동해요 · 주석은 저장하면 PDF에 함께 남아요"; wrapMode: Text.WordWrap; font.pixelSize: Theme.caption; lineHeight: 1.3; color: Theme.inkFaint }
    }
}
