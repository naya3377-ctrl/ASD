// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
MouseArea {
    id: input
    property var controller: bridge
    required property var view
    property bool allowZoom: true
    signal zoomRequested(real amount)
    signal interactionStarted()
    acceptedButtons: Qt.NoButton
    scrollGestureEnabled: true
    onWheel: function(wheel) {
        interactionStarted();
        if (allowZoom && (wheel.modifiers & Qt.ControlModifier)) {
            var amount = wheel.angleDelta.y ? wheel.angleDelta.y/120 : wheel.pixelDelta.y/60;
            zoomRequested(Math.pow(1.12,amount));
            wheel.accepted = true;
            return;
        }
        var lines = controller.wheelScrollLines;
        var unit = lines >= 1000 ? view.height*.9 : lines*20;
        var dx = wheel.pixelDelta.x, dy = wheel.pixelDelta.y;
        if (!dx && !dy) {
            dx = wheel.angleDelta.x/120*unit*controller.wheelSpeed;
            dy = wheel.angleDelta.y/120*unit*controller.wheelSpeed;
        }
        if ((wheel.modifiers & Qt.ShiftModifier) && !dx) { dx=dy; dy=0; }
        // Apply every delta, including fractional high-resolution wheel input.
        // No animation queue, velocity limit, or per-event cap.
        view.cancelFlick();
        var minY = view.originY-view.topMargin;
        var maxY = Math.max(minY,view.originY+view.contentHeight-view.height+view.bottomMargin);
        view.contentY = Math.max(minY,Math.min(maxY,view.contentY-dy));
        view.contentX = Math.max(view.originX,Math.min(view.originX+Math.max(0,view.contentWidth-view.width),view.contentX-dx));
        wheel.accepted = true;
    }
}
