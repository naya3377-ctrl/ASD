// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A side panel that opens and closes without resizing the page on every
// frame: the panel takes its width in one step (or gives it back in one step
// once its content has faded), and only the content moves, fading in over
// 180 ms while sliding 8 px in from the window edge, out over 120 ms.
// Opening again mid-fade continues from where the content is; a finished
// fade never overrides a newer state.
Item {
    id: side
    property bool open: false
    property bool fromLeft: true
    default property alias content: holder.data
    property bool shown: false
    visible: shown
    Item {
        id: holder; width: side.width; height: side.height
        opacity: 0
        transform: Translate { id: slide }
    }
    ParallelAnimation {
        id: entering
        NumberAnimation { target: holder; property: "opacity"; to: 1; duration: Theme.panelInMs; easing.type: Easing.OutCubic }
        NumberAnimation { target: slide; property: "x"; to: 0; duration: Theme.panelInMs; easing.type: Easing.OutCubic }
    }
    ParallelAnimation {
        id: leaving
        NumberAnimation { target: holder; property: "opacity"; to: 0; duration: Theme.panelOutMs; easing.type: Easing.OutCubic }
        NumberAnimation { target: slide; property: "x"; to: side.fromLeft ? -Theme.panelShift : Theme.panelShift; duration: Theme.panelOutMs; easing.type: Easing.OutCubic }
        onFinished: if (!side.open) side.shown = false
    }
    onOpenChanged: {
        if (open) {
            leaving.stop();
            if (!shown) { holder.opacity = 0; slide.x = fromLeft ? -Theme.panelShift : Theme.panelShift; }
            shown = true;
            entering.restart();
        } else {
            entering.stop();
            leaving.restart();
        }
    }
    // Already open when created (a restored tab, the first window): no motion.
    Component.onCompleted: if (open) { shown = true; holder.opacity = 1; slide.x = 0; }
}
