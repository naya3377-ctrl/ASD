// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// The comment being written: a new note, an edit or a reply. It holds only the
// draft; CommentForm shows it inside the list (as the top card for a new note,
// inside the card being edited or answered). Keeping the draft here means it
// survives list scrolling, tab switches and external file opens.
QtObject {
    id: draft
    objectName: "annotationEditor"
    required property var controller
    property bool visible: false
    property var targetData: ({})
    property string text: ""
    property string author: ""
    property string selectedColor: "#ffd54f"
    readonly property string mode: targetData.mode || ""
    readonly property bool canApply: controller.canAnnotate && (mode === "edit" || text.trim().length > 0)
    readonly property bool changed: text !== (targetData.content || "") || selectedColor !== (targetData.color || "#ffd54f")

    onVisibleChanged: controller.setAnnotationEditorVisible(visible)
    property Connections commits: Connections {
        target: draft.controller
        function onAnnotationCommitted() { draft.close(); }
    }

    function close() { visible = false; }
    function compose(data) {
        if (visible) return;
        targetData = data; text = data.content || ""; author = data.author || "";
        selectedColor = data.color || "#ffd54f"; visible = true;
    }
    function apply() { if (canApply) controller.commitAnnotation(targetData, text, author, selectedColor); }
    // True when this draft edits or answers the given list item.
    function belongsTo(item) {
        return visible && mode !== "new" && !!item && targetData.id === item.id && targetData.page === item.page;
    }
}
