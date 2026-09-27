// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The comment panel in two views of the same annotations (see
// bichaek/annotation_views.py):
//  - 메모: what was written (notes, memos on marked words, reply threads),
//    edited as words only, without the marked passage around it;
//  - 형광펜: every marked passage (highlight, underline, strike-out) in page
//    order, like a summary of the document, with its colour and memo, and a
//    button to copy them all as text.
// Clicking an entry jumps to its place on the page; clicking a mark on the
// page scrolls here to it (switching view when needed). Writing happens in
// place: a new memo at the top, an edit or reply inside its entry. The mark
// tools and colours are in the toolbar (comment mode) and call applyMarkup /
// addNote here.
Rectangle {
    id: panel; objectName: "commentsPanel"
    required property var controller
    required property var draft
    property string activeTool: "read"
    property bool allowActions: true
    // The entry under the pointer, outlined on the page by Main.qml.
    property var hoveredItem: null
    // "notes" or "marks".
    property string view: "notes"
    signal toolRequested(string tool)
    color: Theme.surface
    Rectangle { width: Theme.hairline; height: parent.height; color: Theme.line; z: 5 }

    readonly property var notes: controller.annotationNotes
    readonly property var marks: controller.annotationMarks
    readonly property var rows: view === "marks" ? marks : notes
    readonly property var selected: controller.selectedAnnotation
    readonly property string selectedKey: selected && selected.id ? selected.page + ":" + selected.id : ""
    readonly property bool canMark: allowActions && controller.canAnnotate && !controller.ocrBusy
    readonly property var colors: ["#ffd54f","#8ed7ad","#7dbbe6","#ef9bc0","#bcadff"]

    // With words selected the memo goes on them; otherwise pick a place.
    function addNote() {
        if (!settleDraft()) return;
        view = "notes";
        if (controller.textSelection.count > 0) controller.composeSelectionComment();
        else toolRequested("note");
    }
    function applyMarkup(kind) {
        view = "marks";
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
    function indexIn(list, item) {
        if (!item || !item.id) return -1;
        for (var i = 0; i < list.length; ++i)
            if (list[i].id === item.id && list[i].page === item.page) return i;
        return -1;
    }
    // Bring the chosen entry into view, whichever side the choice came from;
    // a mark clicked on the page opens the view that holds it.
    function reveal() {
        var i = indexIn(rows, selected);
        // While a memo is being written the panel stays where the form is.
        if (i < 0 && draft.visible) return;
        if (i < 0) {
            var other = view === "marks" ? notes : marks;
            if (indexIn(other, selected) < 0) return;
            view = view === "marks" ? "notes" : "marks";
            i = indexIn(rows, selected);
        }
        if (i >= 0) comments.positionViewAtIndex(i, ListView.Contain);
    }
    onSelectedKeyChanged: Qt.callLater(reveal)
    // Clicking a mark again (same selection) still brings it into view.
    Connections { target: panel.controller; function onOpenComments() { Qt.callLater(panel.reveal); } }
    // Open on the view that has something in it.
    function settleView() {
        if (view === "notes" && !notes.length && marks.length) view = "marks";
        else if (view === "marks" && !marks.length && notes.length) view = "notes";
    }
    onVisibleChanged: if (visible) settleView()
    onControllerChanged: settleView()
    Connections {
        target: panel.draft
        function onVisibleChanged() {
            if (!panel.draft.visible) return;
            // A new memo is written at the top of the memo list: show it. An
            // edit or reply opens where its entry is, in either view.
            if (panel.draft.mode === "new") { panel.view = "notes"; Qt.callLater(comments.positionViewAtBeginning); }
            else if (panel.indexIn(panel.rows, panel.draft.targetData) < 0 && panel.indexIn(panel.notes, panel.draft.targetData) >= 0) panel.view = "notes";
        }
    }

    // Header: the panel title and the two views.
    Item {
        id: header; width: parent.width; height: 52
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: Theme.gapL; anchors.rightMargin: Theme.gapS; spacing: Theme.gapS
            Text { text: "주석"; font.pixelSize: Theme.title3; font.weight: Font.DemiBold; color: Theme.ink }
            Item { Layout.fillWidth: true }
            BusyIndicator { running: panel.controller.annotationsLoading; visible: running; implicitWidth: 18; implicitHeight: 18 }
            ActionButton { glyph: "close"; iconSize: 16; hint: "주석 목록 닫기"; onClicked: panel.toolRequested("closeComments") }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: Theme.gapM; anchors.rightMargin: Theme.gapM; anchors.topMargin: header.height; anchors.bottomMargin: Theme.gapM; spacing: Theme.gapS
        Segmented {
            Layout.fillWidth: true
            ActionButton { objectName: "commentsNotesTab"; tab: true; compact: true; width: (parent.parent.width-4)/2; text: "메모  " + panel.notes.length; font.features: ({ "tnum": 1 }); active: panel.view === "notes"; onClicked: panel.view = "notes" }
            ActionButton { objectName: "commentsMarksTab"; tab: true; compact: true; width: (parent.parent.width-4)/2; text: "형광펜  " + panel.marks.length; font.features: ({ "tnum": 1 }); active: panel.view === "marks"; onClicked: panel.view = "marks" }
        }
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
            model: panel.rows; spacing: 2
            topMargin: 2; bottomMargin: Theme.gapS
            ScrollBar.vertical: AppScrollBar { }
            // A new memo is written at the top of the memo list.
            header: Loader {
                width: comments.width
                active: panel.view === "notes" && panel.draft.visible && panel.draft.mode === "new"
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
              readonly property bool markView: panel.view === "marks"
              // Page heading above the first entry of each page.
              Item {
                  visible: entry.index===0 || (panel.rows[entry.index-1] && panel.rows[entry.index-1].page!==entry.modelData.page)
                  width: entry.width; height: pageLabel.implicitHeight+(entry.index>0 ? Theme.gapL : Theme.gapXs)+Theme.gapXs
                  Text {
                      id: pageLabel; anchors.bottom: parent.bottom; anchors.bottomMargin: Theme.gapXs; x: Theme.gapS
                      text: (entry.modelData.page+1) + "쪽"; font.pixelSize: Theme.caption; font.weight: Font.DemiBold; color: Theme.inkMuted
                  }
              }
              Item {
                id: card; readonly property var modelData: entry.modelData; readonly property int index: entry.index
                objectName: (entry.markView ? "markCard" : "commentCard")+index
                readonly property bool selected: panel.selected.id===modelData.id && panel.selected.page===modelData.page
                readonly property bool drafting: panel.draft.belongsTo(modelData)
                readonly property bool isMark: ["Highlight","Underline","StrikeOut","Squiggly"].indexOf(modelData.type) >= 0 && !modelData.reply
                x: entry.markView ? 0 : Math.min(modelData.depth,2)*Theme.gapL; width: entry.width-x
                height: (entry.markView ? markLayout.implicitHeight : cardLayout.implicitHeight)+2*Theme.gapM
                // Replies hang from a thin thread on the left.
                Rectangle { visible: !entry.markView && !!card.modelData.reply; x: -Theme.gapS; y: Theme.gapS; width: 2; height: parent.height-2*Theme.gapS; radius: 1; color: Theme.line }
                // One quiet list: the chosen entry sits on the selection colour.
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

                // 메모: the author, what kind of mark it sits on, and the words.
                ColumnLayout {
                    id: cardLayout; visible: !entry.markView
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: Theme.gapM; anchors.rightMargin: Theme.gapM; anchors.topMargin: Theme.gapM; spacing: Theme.gapXs
                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.gapS
                        Rectangle { visible: !card.modelData.reply; width: 8; height: 8; radius: 4; color: card.modelData.color || Theme.inkFaint; border.color: "#3329313a"; border.width: Theme.hairline }
                        Text { text: card.modelData.author || "작성자 없음"; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: Theme.small; font.weight: Font.Medium; color: Theme.ink; textFormat: Text.PlainText }
                        Text {
                            visible: !!card.modelData.created; font.pixelSize: Theme.caption; font.features: ({ "tnum": 1 }); color: Theme.inkMuted; textFormat: Text.PlainText
                            text: card.modelData.created.slice(0,2)==="D:" ? card.modelData.created.slice(2,6)+"."+card.modelData.created.slice(6,8)+"."+card.modelData.created.slice(8,10) : card.modelData.created
                        }
                    }
                    // One line of context for a memo on marked words; the whole
                    // passage lives in the 형광펜 view, and leaves while editing.
                    Text {
                        objectName: "commentContext"+card.index
                        Layout.fillWidth: true; elide: Text.ElideRight; maximumLineCount: 1; textFormat: Text.PlainText
                        text: card.modelData.reply ? "답글"
                            : (card.modelData.label + (card.isMark && card.modelData.quote && !card.drafting ? "  ·  " + card.modelData.quote.replace(/\s+/g," ") : ""))
                        font.pixelSize: Theme.caption; color: Theme.inkMuted
                    }
                    Text {
                        visible: !card.drafting || panel.draft.mode === "reply"; Layout.fillWidth: true; Layout.topMargin: 2
                        text: card.modelData.content || (card.modelData.state ? "검토 상태: "+card.modelData.state : "내용 없는 주석")
                        wrapMode: Text.Wrap; maximumLineCount: card.selected ? 12 : 4; elide: Text.ElideRight
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
                        Layout.fillWidth: true; active: !entry.markView && card.drafting; visible: active; Layout.topMargin: Theme.gapS
                        sourceComponent: CommentForm { draft: panel.draft }
                    }
                }

                // 형광펜: the marked passage in its colour, then its memo.
                RowLayout {
                    id: markLayout; visible: entry.markView
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: Theme.gapM; anchors.rightMargin: Theme.gapM; anchors.topMargin: Theme.gapM; spacing: Theme.gapM
                    Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 4; radius: 2; color: card.modelData.color || Theme.inkFaint }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: Theme.gapXs
                        Text {
                            objectName: "markQuote"+card.index
                            Layout.fillWidth: true; textFormat: Text.PlainText; wrapMode: Text.Wrap
                            text: card.modelData.quote ? card.modelData.quote.replace(/\s+/g," ") : "(글자를 읽을 수 없는 표시)"
                            maximumLineCount: card.selected ? 12 : 4; elide: Text.ElideRight
                            font.pixelSize: Theme.body; lineHeight: 1.35; color: card.modelData.quote ? Theme.ink : Theme.inkMuted
                            font.underline: card.modelData.type === "Underline" || card.modelData.type === "Squiggly"
                            font.strikeout: card.modelData.type === "StrikeOut"
                        }
                        Text {
                            Layout.fillWidth: true; elide: Text.ElideRight; textFormat: Text.PlainText
                            text: card.modelData.label + (card.modelData.author ? "  ·  " + card.modelData.author : "") + (card.modelData.replies > 0 ? "  ·  답글 " + card.modelData.replies : "")
                            font.pixelSize: Theme.caption; color: Theme.inkMuted
                        }
                        // The memo on this passage, if there is one.
                        RowLayout {
                            visible: !!card.modelData.note && !card.drafting; Layout.fillWidth: true; spacing: Theme.gapXs; Layout.topMargin: 2
                            Icon { name: "note"; size: 14; tone: Theme.inkMuted; Layout.alignment: Qt.AlignTop; Layout.topMargin: 2 }
                            Text { objectName: "markNote"+card.index; Layout.fillWidth: true; text: card.modelData.note || ""; wrapMode: Text.Wrap; maximumLineCount: card.selected ? 8 : 2; elide: Text.ElideRight; font.pixelSize: Theme.small; lineHeight: 1.3; color: Theme.inkSoft; textFormat: Text.PlainText }
                        }
                        Text { visible: !card.modelData.editable && card.selected; Layout.fillWidth: true; text: "읽기 전용 · 원본 주석 보존"; font.pixelSize: Theme.caption; color: Theme.inkMuted }
                        // Chosen: its colour, a memo, or remove it.
                        RowLayout {
                            visible: card.selected && card.modelData.editable && !card.drafting; spacing: 0; Layout.topMargin: Theme.gapXs; Layout.fillWidth: true
                            Repeater {
                                model: panel.colors
                                delegate: Item {
                                    required property string modelData
                                    objectName: "markColor_"+modelData.slice(1)
                                    width: 24; height: 32
                                    readonly property bool chosen: String(card.modelData.color).toLowerCase() === modelData
                                    Rectangle { anchors.centerIn: parent; width: 20; height: 20; radius: 10; color: "transparent"; border.color: Theme.accent; border.width: 2; visible: parent.chosen }
                                    Rectangle { anchors.centerIn: parent; width: 14; height: 14; radius: 7; color: parent.modelData; border.color: "#2629313a"; border.width: Theme.hairline }
                                    MouseArea {
                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        enabled: panel.allowActions && panel.controller.canAnnotate && !panel.draft.visible && !panel.controller.busy
                                        onClicked: panel.controller.recolorAnnotation(card.modelData.page, card.modelData.id, parent.modelData)
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                            ActionButton { objectName: "markMemo"+card.index; compact: true; outlined: true; text: card.modelData.content && String(card.modelData.content).trim() ? "메모 수정" : "메모 달기"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: { panel.settleDraft(); panel.controller.editSelectedAnnotation("edit"); } }
                            ActionButton { glyph: "delete"; Layout.leftMargin: 2; hint: "표시와 메모 삭제"; enabled: panel.allowActions && panel.controller.canAnnotate; onClicked: panel.controller.deleteSelectedAnnotation() }
                        }
                        Loader {
                            Layout.fillWidth: true; active: entry.markView && card.drafting; visible: active; Layout.topMargin: Theme.gapS
                            sourceComponent: CommentForm { draft: panel.draft }
                        }
                    }
                }
              }
            }
            // Nothing yet: a short note on how to start.
            Column {
                visible: !comments.count && !panel.controller.annotationsLoading && !(panel.draft.visible && panel.view === "notes")
                anchors.centerIn: parent; width: parent.width-2*Theme.gapL; spacing: Theme.gapS
                Icon { objectName: "commentsEmptyIcon"; anchors.horizontalCenter: parent.horizontalCenter; name: panel.view === "marks" ? "highlight" : "note"; size: 28; tone: Theme.inkFaint }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: panel.view === "marks" ? "아직 형광펜이 없어요" : "아직 메모가 없어요"; font.pixelSize: Theme.body; font.weight: Font.Medium; color: Theme.ink; topPadding: Theme.gapXs }
                Text {
                    width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; font.pixelSize: Theme.small; lineHeight: 1.4; color: Theme.inkMuted
                    text: panel.view === "marks" ? "글자를 드래그한 뒤 도구줄의 형광펜·밑줄·취소선을 누르면 여기에 쪽 순서대로 모여요."
                        : "글자를 드래그한 뒤 도구줄의 메모를 누르거나, 선택 없이 메모를 눌러 페이지에서 자리를 고르세요. 형광펜은 옆 탭에 따로 모여요."
                }
            }
        }
        // 형광펜: copy the whole summary as text.
        RowLayout {
            visible: panel.view === "marks" && panel.marks.length > 0; Layout.fillWidth: true; spacing: Theme.gapS
            ActionButton { objectName: "copyMarksButton"; compact: true; outlined: true; text: "모두 복사"; hint: "표시한 글을 쪽 순서대로, 메모와 함께 텍스트로 복사해요"; onClicked: panel.controller.copyAnnotationSummary() }
            Text { Layout.fillWidth: true; text: "쪽 순서대로 텍스트로 복사해요"; wrapMode: Text.WordWrap; font.pixelSize: Theme.caption; color: Theme.inkMuted }
        }
        Text {
            visible: panel.view === "notes"
            Layout.fillWidth: true; Layout.leftMargin: Theme.gapXs; text: "주석을 누르면 그 위치로 이동해요 · 저장하면 PDF에 함께 남아요"; wrapMode: Text.WordWrap; font.pixelSize: Theme.caption; lineHeight: 1.35; color: Theme.inkMuted
        }
    }
}
