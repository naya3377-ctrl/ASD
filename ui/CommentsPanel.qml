// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Comment list grouped by page. Clicking a comment jumps to its place on the
// page; clicking a mark on the page scrolls here to its comment. Writing
// happens inside the list: a new note is at the top, an edit or reply opens
// in place. The mark tools and colours are in the toolbar (comment mode) and
// call applyMarkup / addNote here.
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
    Rectangle { width: Theme.hairline; height: parent.height; color: Theme.line; z: 5 }

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

    // Header: the panel title with the count beside it.
    Item {
        id: header; width: parent.width; height: 52
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: Theme.gapL; anchors.rightMargin: Theme.gapS; spacing: Theme.gapS
            Text { text: "주석"; font.pixelSize: Theme.title3; font.weight: Font.DemiBold; color: Theme.ink }
            Text {
                objectName: "commentCount"; text: panel.controller.annotations.length
                font.pixelSize: Theme.small; font.features: ({ "tnum": 1 }); color: Theme.inkMuted
            }
            Item { Layout.fillWidth: true }
            BusyIndicator { running: panel.controller.annotationsLoading; visible: running; implicitWidth: 18; implicitHeight: 18 }
            ActionButton { glyph: "close"; iconSize: 16; hint: "주석 목록 닫기"; onClicked: panel.toolRequested("closeComments") }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: Theme.gapM; anchors.rightMargin: Theme.gapM; anchors.topMargin: header.height; anchors.bottomMargin: Theme.gapM; spacing: Theme.gapS
        RowLayout {
            Layout.fillWidth: true; Layout.leftMargin: Theme.gapXs; spacing: Theme.gapS
            Text { text: "작성자"; font.pixelSize: Theme.small; color: Theme.inkMuted }
            TextField {
                id: authorInput; objectName: "annotationAuthorInput"; Layout.fillWidth: true; text: panel.controller.annotationAuthor
                placeholderText: "이름"; selectByMouse: true; font.pixelSize: Theme.body; color: Theme.ink; implicitHeight: Theme.control
                leftPadding: 10; placeholderTextColor: Theme.inkFaint; selectionColor: Theme.selection; selectedTextColor: Theme.ink
                background: Rectangle {
                    radius: Theme.radius; color: Theme.field; border.width: authorInput.activeFocus ? 2 : Theme.hairline
                    border.color: authorInput.activeFocus ? Theme.focusRing : Theme.line
                }
                onEditingFinished: panel.controller.setAnnotationAuthor(text)
            }
        }

        ListView {
            id: comments; objectName: "commentsList"
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.topMargin: Theme.gapXs; clip: true
            model: panel.controller.annotations; spacing: 2
            topMargin: 2; bottomMargin: Theme.gapS
            ScrollBar.vertical: AppScrollBar { }
            // A new note is written at the top of the list.
            header: Loader {
                width: comments.width
                active: panel.draft.visible && panel.draft.mode === "new"
                height: active && item ? item.implicitHeight : 0
                sourceComponent: Item {
                    implicitHeight: newForm.implicitHeight + 2*Theme.gapM + Theme.gapM   // the form, then a gap before the list
                    Rectangle {
                        width: parent.width; height: parent.height - Theme.gapM
                        radius: Theme.radiusLarge; color: Theme.raised; border.color: Theme.accent; border.width: 1.5
                        CommentForm { id: newForm; draft: panel.draft; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: Theme.gapM }
                    }
                }
            }
            delegate: Column {
              id: entry; required property var modelData; required property int index
              width: comments.width; spacing: 0
              // Page heading above the first comment of each page.
              Item {
                  visible: entry.index===0 || panel.controller.annotations[entry.index-1].page!==entry.modelData.page
                  width: entry.width; height: pageLabel.implicitHeight+(entry.index>0 ? Theme.gapL : Theme.gapXs)+Theme.gapXs
                  Text {
                      id: pageLabel; anchors.bottom: parent.bottom; anchors.bottomMargin: Theme.gapXs; x: Theme.gapS
                      text: (entry.modelData.page+1) + "쪽"; font.pixelSize: Theme.caption; font.weight: Font.DemiBold; color: Theme.inkMuted
                  }
              }
              Item {
                id: card; readonly property var modelData: entry.modelData; readonly property int index: entry.index
                objectName: "commentCard"+index
                readonly property bool selected: panel.selected.id===modelData.id && panel.selected.page===modelData.page
                readonly property bool drafting: panel.draft.belongsTo(modelData)
                x: Math.min(modelData.depth,2)*Theme.gapL; width: entry.width-x
                height: cardLayout.implicitHeight+2*Theme.gapM
                // Replies hang from a thin thread on the left.
                Rectangle { visible: !!card.modelData.reply; x: -Theme.gapS; y: Theme.gapS; width: 2; height: parent.height-2*Theme.gapS; radius: 1; color: Theme.line }
                // One quiet list: the chosen comment sits on the selection colour.
                Rectangle {
                    anchors.fill: parent; radius: Theme.radiusLarge
                    color: card.selected ? Theme.accentSoft : cardHover.hovered ? Theme.hover : "transparent"
                    border.width: card.drafting ? 1.5 : 0; border.color: Theme.accent
                    Behavior on color { ColorAnimation { duration: Theme.listMs; easing.type: Easing.OutCubic } }
                }
                HoverHandler { id: cardHover; onHoveredChanged: panel.hoveredItem = hovered ? card.modelData : (panel.hoveredItem === card.modelData ? null : panel.hoveredItem) }
                TapHandler {
                    enabled: !card.drafting
                    onTapped: panel.choose(card.modelData)
                    onDoubleTapped: { panel.choose(card.modelData); if(card.modelData.editable) panel.controller.editSelectedAnnotation("edit"); }
                }
                ColumnLayout {
                    id: cardLayout; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: Theme.gapM; anchors.rightMargin: Theme.gapM; anchors.topMargin: Theme.gapM; spacing: Theme.gapXs
                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.gapS
                        // The mark's own colour, as a small dot.
                        Rectangle { visible: !card.modelData.reply; width: 8; height: 8; radius: 4; color: card.modelData.color || Theme.inkFaint; border.color: "#3329313a"; border.width: Theme.hairline }
                        Text { text: card.modelData.author || "작성자 없음"; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: Theme.small; font.weight: Font.Medium; color: Theme.ink; textFormat: Text.PlainText }
                        Text {
                            visible: !!card.modelData.created; font.pixelSize: Theme.caption; font.features: ({ "tnum": 1 }); color: Theme.inkMuted; textFormat: Text.PlainText
                            text: card.modelData.created.slice(0,2)==="D:" ? card.modelData.created.slice(2,6)+"."+card.modelData.created.slice(6,8)+"."+card.modelData.created.slice(8,10) : card.modelData.created
                        }
                    }
                    Text { text: card.modelData.reply ? "답글" : card.modelData.label; font.pixelSize: Theme.caption; color: Theme.inkMuted; textFormat: Text.PlainText }
                    // The marked words, set off by a thin rule like a quotation.
                    RowLayout {
                        visible: !!card.modelData.quote && !card.modelData.reply; Layout.fillWidth: true; spacing: Theme.gapS; Layout.topMargin: 2
                        Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 2; radius: 1; color: Theme.lineStrong }
                        Text {
                            Layout.fillWidth: true
                            text: card.modelData.quote.replace(/\s+/g," "); wrapMode: Text.Wrap
                            maximumLineCount: card.selected ? 4 : 2; elide: Text.ElideRight
                            font.pixelSize: Theme.small; lineHeight: 1.3; color: Theme.inkSoft; textFormat: Text.PlainText
                        }
                    }
                    Text {
                        visible: !card.drafting || panel.draft.mode === "reply"; Layout.fillWidth: true; Layout.topMargin: 2
                        text: card.modelData.content || (card.modelData.state ? "검토 상태: "+card.modelData.state : card.modelData.quote ? "" : "내용 없는 주석")
                        wrapMode: Text.Wrap; maximumLineCount: card.selected ? 8 : 3; elide: Text.ElideRight
                        font.pixelSize: Theme.body; lineHeight: 1.35; color: card.modelData.content ? Theme.ink : Theme.inkMuted; textFormat: Text.PlainText
                    }
                    Text { visible: !card.modelData.editable && card.selected; Layout.fillWidth: true; text: "읽기 전용 · 원본 주석 보존"; font.pixelSize: Theme.caption; color: Theme.inkMuted }
                    RowLayout {
                        visible: card.selected && card.modelData.editable && !card.drafting; spacing: Theme.gapS; Layout.topMargin: Theme.gapXs
                        ActionButton { objectName: "editComment"+card.index; compact: true; outlined: true; text: "수정"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: { panel.settleDraft(); panel.controller.editSelectedAnnotation("edit"); } }
                        ActionButton { objectName: "replyComment"+card.index; compact: true; outlined: true; text: "답글"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: { panel.settleDraft(); panel.controller.editSelectedAnnotation("reply"); } }
                        Item { Layout.fillWidth: true }
                        ActionButton { glyph: "delete"; hint: "주석과 답글 삭제"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: panel.controller.deleteSelectedAnnotation() }
                    }
                    Loader {
                        Layout.fillWidth: true; active: card.drafting; visible: active; Layout.topMargin: Theme.gapS
                        sourceComponent: CommentForm { draft: panel.draft }
                    }
                }
              }
            }
            // Nothing yet: a short note on how to start.
            Column {
                visible: !comments.count && !panel.controller.annotationsLoading && !panel.draft.visible
                anchors.centerIn: parent; width: parent.width-2*Theme.gapL; spacing: Theme.gapS
                Icon { objectName: "commentsEmptyIcon"; anchors.horizontalCenter: parent.horizontalCenter; name: "note"; size: 28; tone: Theme.inkFaint }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: "아직 주석이 없어요"; font.pixelSize: Theme.body; font.weight: Font.Medium; color: Theme.ink; topPadding: Theme.gapXs }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; text: "글자를 드래그한 뒤 도구줄의 형광펜이나 메모를 눌러 보세요. 선택 없이 메모를 누르면 페이지에서 자리를 고를 수 있어요."; font.pixelSize: Theme.small; lineHeight: 1.4; color: Theme.inkMuted }
            }
        }
        Text { Layout.fillWidth: true; Layout.leftMargin: Theme.gapXs; text: "주석을 누르면 그 위치로 이동해요 · 저장하면 PDF에 함께 남아요"; wrapMode: Text.WordWrap; font.pixelSize: Theme.caption; lineHeight: 1.35; color: Theme.inkMuted }
    }
}
